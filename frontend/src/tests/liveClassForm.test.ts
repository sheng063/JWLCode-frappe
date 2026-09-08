import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import {
	createMemoryHistory,
	createRouter,
	RouterView,
	type Router,
} from 'vue-router'
import { defineComponent, h } from 'vue'
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore'

dayjs.extend(utc)
dayjs.extend(timezone)
dayjs.extend(isSameOrBefore)

vi.stubGlobal('__', (text: string) => text)
enableAutoUnmount(afterEach)

const {
	batchResource,
	liveClassList,
	createResourceMock,
	createListResourceMock,
	getCachedListResourceMock,
	zoomSubmit,
	meetSubmit,
	updateSubmit,
	existing,
} = vi.hoisted(() => {
	// @/utils reaches plyr, which touches matchMedia at import time.
	window.matchMedia ??= (() => ({
		matches: false,
		addEventListener: () => {},
		removeEventListener: () => {},
	})) as unknown as typeof window.matchMedia
	return {
		batchResource: {
			data: null as Record<string, unknown> | null,
			loading: false,
			fetched: true,
			reload: () => {},
		},
		liveClassList: { data: [] as Record<string, unknown>[], reload: vi.fn() },
		createResourceMock: vi.fn(),
		createListResourceMock: vi.fn(),
		getCachedListResourceMock: vi.fn(),
		zoomSubmit: vi.fn(),
		meetSubmit: vi.fn(),
		updateSubmit: vi.fn(),
		existing: { doc: null as Record<string, unknown> | null },
	}
})

// HeaderButton wraps frappe-ui's Button in a Tooltip below the mobile
// breakpoint, and the hand-written frappe-ui mock here has no Tooltip. Stub it
// down to the bare button so the fallthrough attrs the assertions use
// (data-testid, the click handler) still land where they did before.
vi.mock('@/components/HeaderButton.vue', () => ({
	default: {
		inheritAttrs: false,
		template: `<button v-bind="$attrs" />`,
	},
}))

vi.mock('frappe-ui', () => ({
	createResource: createResourceMock,
	createListResource: createListResourceMock,
	getCachedListResource: getCachedListResourceMock,
	toast: { success: vi.fn(), error: vi.fn() },
	Dialog: {
		name: 'Dialog',
		props: ['open', 'title', 'size'],
		emits: ['update:open'],
		template: `<div v-if="open" role="dialog"><slot name="title" /><slot /><slot name="actions" /></div>`,
	},
	Button: {
		inheritAttrs: false,
		template: `<button v-bind="$attrs"><slot name="icon" /><slot name="prefix" /><slot /></button>`,
	},
	FormControl: {
		props: ['modelValue', 'label', 'type', 'options'],
		emits: ['update:modelValue'],
		template: `<label>{{ label }}<input :value="modelValue" @input="$emit('update:modelValue', $event.target.value)" /></label>`,
	},
	// Renders its label, as the real Combobox does: a stub that drops it makes
	// "every field is labelled" pass by omission.
	Combobox: {
		inheritAttrs: false,
		props: ['label', 'modelValue'],
		emits: ['update:modelValue'],
		template: `<div><label v-if="label">{{ label }}<input :value="modelValue" @input="$emit('update:modelValue', $event.target.value)" /></label><slot /></div>`,
	},
	Tooltip: { inheritAttrs: false, template: `<div><slot /></div>` },
}))

vi.mock('@/components/Modals/LiveClassAttendance.vue', () => ({
	default: defineComponent({ render: () => h('div') }),
}))

// @ts-expect-error a JS SFC has no generated types (TS7016) — the same gap
// every test importing a non-`lang="ts"` component in this suite hits.
import LiveClassForm from '@/pages/Forms/LiveClassForm.vue'
// @ts-expect-error same TS7016; LiveClass.vue predates this branch.
import LiveClass from '@/pages/Batches/components/LiveClass.vue'

const BATCH_URL = 'lms.lms.utils.get_batch_details'
const ZOOM_URL = 'lms.lms.doctype.lms_batch.lms_batch.create_live_class'
const UPDATE_URL =
	'lms.lms.doctype.lms_live_class.lms_live_class.update_live_class'
const MEET_URL =
	'lms.lms.doctype.lms_batch.lms_batch.create_google_meet_live_class'

const Parent = defineComponent({
	render: () => h('div', ['BATCH', h(RouterView)]),
})

const makeRouter = (): Router =>
	createRouter({
		history: createMemoryHistory(),
		routes: [
			{
				path: '/batches/:batchName',
				name: 'BatchDetail',
				component: Parent,
				props: true,
				children: [
					{
						path: 'live-class/:liveClassName/edit',
						name: 'EditLiveClass',
						component: LiveClassForm,
						props: true,
					},
					{
						path: 'live-class/new',
						name: 'NewLiveClass',
						component: LiveClassForm,
						props: true,
					},
				],
			},
		],
	})

const provide = (user: Record<string, unknown>) => ({
	$user: { data: user },
	$dayjs: dayjs,
})

const mountForm = async (router: Router, user: Record<string, unknown>) => {
	const wrapper = mount(defineComponent({ render: () => h(RouterView) }), {
		global: {
			plugins: [router],
			provide: provide(user),
			stubs: { teleport: true },
			mocks: { __: (text: string) => text },
		},
	})
	await flushPromises()
	return wrapper
}

const moderator = { name: 'mod@example.com', is_moderator: true }
const student = { name: 'student@example.com' }

const norm = (text: string) =>
	text
		.replace(/\s+/g, ' ')
		.replace(/\s*\*$/, '')
		.trim()

const FIELD_LABELS = [
	'Title',
	'Date',
	'Duration (in minutes)',
	'Time',
	'Timezone',
	'Auto Recording',
	'Description',
]

const fillValidClass = async (wrapper: ReturnType<typeof mount>) => {
	for (const [label, value] of Object.entries({
		Title: 'A live class',
		Date: dayjs().add(2, 'day').format('YYYY-MM-DD'),
		Time: '10:00',
		'Duration (in minutes)': '60',
		Timezone: 'Asia/Shanghai',
	})) {
		const field = wrapper
			.findAll('label')
			.find((node) => norm(node.text()) === label)!
		await field.find('input').setValue(value)
	}
}

describe('LiveClassForm as a route', () => {
	beforeEach(() => {
		zoomSubmit.mockReset()
		meetSubmit.mockReset()
		updateSubmit.mockReset()
		existing.doc = null
		liveClassList.data = []
		liveClassList.reload.mockReset()
		getCachedListResourceMock.mockReset()
		getCachedListResourceMock.mockReturnValue(liveClassList)
		createListResourceMock.mockReset()
		createListResourceMock.mockReturnValue(liveClassList)
		createResourceMock.mockReset()
		createResourceMock.mockImplementation((options: any) => {
			if (options.url === BATCH_URL) return batchResource
			if (options.url === UPDATE_URL)
				return { submit: updateSubmit, loading: false }
			if (options.url === 'frappe.client.get') {
				const resource = { data: existing.doc, error: null, loading: false }
				if (options.auto && existing.doc)
					queueMicrotask(() => options.onSuccess(existing.doc))
				return resource
			}
			if (options.url === ZOOM_URL)
				return { submit: zoomSubmit, loading: false, data: null }
			if (options.url === MEET_URL)
				return { submit: meetSubmit, loading: false, data: null }
			return { submit: vi.fn(), loading: false, data: null }
		})
		batchResource.data = {
			name: 'B1',
			conferencing_provider: 'Zoom',
			zoom_account: 'zoom-1',
		}
		batchResource.loading = false
		Object.defineProperty(window, 'innerWidth', {
			value: 1024,
			writable: true,
			configurable: true,
		})
	})

	it('mounts straight from the URL with no parent page mounted', async () => {
		const router = makeRouter()
		await router.push('/batches/B1/live-class/new')
		const wrapper = await mountForm(router, moderator)
		expect(wrapper.html()).toContain('Create a Live Class')
		expect(wrapper.find('[data-testid="live-class-fields"]').exists()).toBe(
			true
		)
	})

	it('fetches its own batch context for the batch in the URL', async () => {
		// The conferencing provider and its account come from get_batch_details.
		// This is the form's OWN fetch — BatchDetail's resource carries no cache
		// key, so there is no instance to share and none is claimed.
		const router = makeRouter()
		await router.push('/batches/B1/live-class/new')
		await mountForm(router, moderator)
		const batchCall = createResourceMock.mock.calls.find(
			(call) => call[0].url === BATCH_URL
		)
		expect(batchCall).toBeDefined()
		expect(batchCall?.[0].cache).toBeUndefined()
		expect(batchCall?.[0].makeParams()).toEqual({ batch: 'B1' })
	})

	it('refuses for a user who is not a batch admin', async () => {
		const router = makeRouter()
		await router.push('/batches/B1/live-class/new')
		const wrapper = await mountForm(router, student)
		expect(wrapper.find('[data-testid="live-class-fields"]').exists()).toBe(
			false
		)
		expect(wrapper.html()).toContain('not permitted')
	})

	it('refuses when the batch has no conferencing account', async () => {
		batchResource.data = { name: 'B1', conferencing_provider: 'Zoom' }
		const router = makeRouter()
		await router.push('/batches/B1/live-class/new')
		const wrapper = await mountForm(router, moderator)
		expect(wrapper.find('[data-testid="live-class-fields"]').exists()).toBe(
			false
		)
		expect(wrapper.html()).toContain('conferencing provider')
	})

	it('carries every field of the live-class form', async () => {
		const router = makeRouter()
		await router.push('/batches/B1/live-class/new')
		const wrapper = await mountForm(router, moderator)

		const labels = wrapper
			.find('[data-testid="live-class-fields"]')
			.findAll('label')
			.map((label) => norm(label.text()))
			.filter((text) => text !== '')
		for (const label of FIELD_LABELS) expect(labels).toContain(label)
		expect(labels).toHaveLength(FIELD_LABELS.length)
	})

	it('submits through the endpoint the batch provider selects', async () => {
		const router = makeRouter()
		await router.push('/batches/B1/live-class/new')
		const wrapper = await mountForm(router, moderator)
		await fillValidClass(wrapper)
		await wrapper.find('[data-testid="live-class-save"]').trigger('click')
		expect(zoomSubmit).toHaveBeenCalledTimes(1)
		expect(meetSubmit).not.toHaveBeenCalled()

		batchResource.data = {
			name: 'B1',
			conferencing_provider: 'Google Meet',
			google_meet_account: 'meet-1',
		}
		const meetRouter = makeRouter()
		await meetRouter.push('/batches/B1/live-class/new')
		const meetWrapper = await mountForm(meetRouter, moderator)
		await fillValidClass(meetWrapper)
		await meetWrapper.find('[data-testid="live-class-save"]').trigger('click')
		expect(meetSubmit).toHaveBeenCalledTimes(1)
	})

	it('refreshes the Classes tab list after a create, by cache key', async () => {
		// The `reloadLiveClasses` defineModel is gone with the modal; the tab's
		// list resource is found by the key LiveClass.vue registers it under.
		const router = makeRouter()
		await router.push('/batches/B1/live-class/new')
		const wrapper = await mountForm(router, moderator)
		zoomSubmit.mockImplementation(
			(_doc: unknown, options: { onSuccess: () => void }) => options.onSuccess()
		)
		await fillValidClass(wrapper)
		await wrapper.find('[data-testid="live-class-save"]').trigger('click')
		await flushPromises()
		expect(getCachedListResourceMock).toHaveBeenCalledWith([
			'liveClasses',
			'B1',
		])
		expect(liveClassList.reload).toHaveBeenCalledTimes(1)
	})

	it('mobile: the back control pops the router back to the page', async () => {
		const router = makeRouter()
		await router.push('/batches/B1#classes')
		await router.push({
			name: 'NewLiveClass',
			params: { batchName: 'B1' },
			hash: '#classes',
			state: { lmsFormEntry: true },
		})
		Object.defineProperty(window, 'innerWidth', {
			value: 390,
			writable: true,
			configurable: true,
		})
		const wrapper = await mountForm(router, moderator)
		await wrapper.find('[data-testid="form-shell-back"]').trigger('click')
		await flushPromises()
		expect(router.currentRoute.value.fullPath).toBe('/batches/B1#classes')
	})

	it('desktop: dismissing the Dialog pops the router back to the page', async () => {
		const router = makeRouter()
		await router.push('/batches/B1#classes')
		await router.push({
			name: 'NewLiveClass',
			params: { batchName: 'B1' },
			hash: '#classes',
			state: { lmsFormEntry: true },
		})
		const wrapper = await mountForm(router, moderator)
		await wrapper
			.findComponent({ name: 'Dialog' })
			.vm.$emit('update:open', false)
		await flushPromises()
		expect(router.currentRoute.value.name).toBe('BatchDetail')
	})

	it('does not submit an empty form', async () => {
		const router = makeRouter()
		await router.push('/batches/B1/live-class/new')
		const wrapper = await mountForm(router, moderator)
		await wrapper.find('[data-testid="live-class-save"]').trigger('click')
		expect(zoomSubmit).not.toHaveBeenCalled()
	})

	it('loads an existing class and saves edits without creating a new meeting', async () => {
		existing.doc = {
			name: 'LC1',
			batch_name: 'B1',
			title: 'Original class',
			description: 'Original notes',
			date: '2020-01-01',
			time: '9:30:00',
			duration: 60,
			timezone: 'Asia/Tokyo',
			auto_recording: 'No Recording',
			conferencing_provider: 'Zoom',
			modified: '2026-01-01 09:00:00',
		}
		const router = makeRouter()
		await router.push('/batches/B1/live-class/LC1/edit#classes')
		const wrapper = await mountForm(router, moderator)
		const description = wrapper
			.findAll('label')
			.find((node) => norm(node.text()) === 'Description')!
		await description.find('input').setValue('Updated notes')
		updateSubmit.mockImplementation((_values, options) => options.onSuccess())
		await wrapper.find('[data-testid="live-class-save"]').trigger('click')
		await flushPromises()
		expect(updateSubmit).toHaveBeenCalledWith(
			expect.objectContaining({
				title: 'Original class',
				description: 'Updated notes',
				time: '09:30',
				timezone: 'Asia/Tokyo',
			}),
			expect.anything()
		)
		expect(zoomSubmit).not.toHaveBeenCalled()
		expect(meetSubmit).not.toHaveBeenCalled()
		expect(getCachedListResourceMock).toHaveBeenCalledWith([
			'liveClasses',
			'B1',
		])
		expect(router.currentRoute.value.fullPath).toBe('/batches/B1#classes')
		const options = createResourceMock.mock.calls.find(
			([opts]) => opts.url === UPDATE_URL
		)![0]
		expect(options.makeParams({ title: 'Updated' })).toMatchObject({
			name: 'LC1',
			modified: existing.doc.modified,
		})
	})

	it('refuses a class belonging to a different batch', async () => {
		existing.doc = { name: 'LC1', batch_name: 'B2', time: '09:00:00' }
		const router = makeRouter()
		await router.push('/batches/B1/live-class/LC1/edit')
		const wrapper = await mountForm(router, moderator)
		expect(wrapper.text()).toContain(
			'This live class does not belong to this batch.'
		)
		expect(wrapper.find('[data-testid="live-class-save"]').exists()).toBe(false)
	})

	it('closing a DEEP-LINKED form keeps the tab hash (C2)', async () => {
		const router = makeRouter()
		await router.push('/batches/B1/live-class/new#classes')
		const wrapper = await mountForm(router, moderator)
		await wrapper
			.findComponent({ name: 'Dialog' })
			.vm.$emit('update:open', false)
		await flushPromises()
		expect(router.currentRoute.value.fullPath).toBe('/batches/B1#classes')
	})
})

describe('the Classes tab opener', () => {
	beforeEach(() => {
		createListResourceMock.mockReset()
		liveClassList.data = []
		createListResourceMock.mockReturnValue(liveClassList)
		Object.defineProperty(window, 'innerWidth', {
			value: 1024,
			writable: true,
			configurable: true,
		})
	})

	const mountTab = async (router: Router) =>
		mount(LiveClass, {
			props: {
				batch: {
					data: {
						name: 'B1',
						conferencing_provider: 'Zoom',
						zoom_account: 'zoom-1',
					},
				},
			},
			global: {
				plugins: [router],
				provide: provide(moderator),
				mocks: { __: (text: string) => text },
			},
		})

	it('registers its list under the key the form refreshes', async () => {
		const router = makeRouter()
		await router.push('/batches/B1#classes')
		await mountTab(router)
		expect(createListResourceMock).toHaveBeenCalledWith(
			expect.objectContaining({ cache: ['liveClasses', 'B1'] })
		)
	})

	it('opens the form route carrying the current tab hash (C2)', async () => {
		const router = makeRouter()
		await router.push('/batches/B1#classes')
		const wrapper = await mountTab(router)
		await wrapper.find('[data-testid="live-class-add"]').trigger('click')
		await flushPromises()
		expect(router.currentRoute.value.fullPath).toBe(
			'/batches/B1/live-class/new#classes'
		)
	})
	it('opens the edit route for an existing class', async () => {
		liveClassList.data = [
			{
				name: 'LC1',
				title: 'Edit me',
				date: '2020-01-01',
				time: '10:00:00',
				duration: 60,
				attendees: 0,
			},
		]
		const router = makeRouter()
		await router.push('/batches/B1#classes')
		const wrapper = await mountTab(router)
		await wrapper
			.findAll('button')
			.find((button) => button.text() === 'Edit')!
			.trigger('click')
		await flushPromises()
		expect(router.currentRoute.value.fullPath).toBe(
			'/batches/B1/live-class/LC1/edit#classes'
		)
	})
})
