<template>
	<div class="creations-page">
		<div class="breadcrumb">
			个人空间 <span>/</span> <span class="text-ink-gray-8">我的作品</span>
		</div>
		<header class="page-heading">
			<div>
				<h1>我的作品</h1>
				<p>保存每一次灵感，继续你的代码创作</p>
			</div>
			<RouterLink :to="{ name: 'Creation' }" class="new-creation"
				><span class="lucide-plus size-4" />新建作品</RouterLink
			>
		</header>
		<p class="creation-count" aria-live="polite">
			{{
				loading
					? '正在加载作品…'
					: error
						? '作品加载失败'
						: `共 ${total} 个作品`
			}}
		</p>
		<div class="filter-bar">
			<form class="search-field" role="search" @submit.prevent="search">
				<button type="submit" aria-label="搜索">
					<span class="lucide-search size-4" /></button
				><input
					v-model="query"
					aria-label="搜索作品名称"
					maxlength="140"
					placeholder="搜索作品名称…"
				/><button
					v-if="query"
					type="button"
					aria-label="清除搜索"
					@click="clearSearch"
				>
					<span class="lucide-x size-4" />
				</button>
			</form>
			<div class="language-filter" aria-label="编程语言筛选">
				<button
					v-for="option in languages"
					:key="option.value"
					:class="{ selected: language === option.value }"
					:aria-pressed="language === option.value"
					@click="filterLanguage(option.value)"
				>
					{{ option.label }}
				</button>
			</div>
			<label class="sort-field"
				><span class="sr-only">排序方式</span
				><select v-model="sort" aria-label="排序方式" @change="search">
					<option value="modified">最近修改</option>
					<option value="created">最近创建</option>
					<option value="title">名称排序</option>
				</select></label
			>
		</div>
		<p v-if="error" role="alert" class="notice text-ink-red-4">
			{{ error }} <button class="underline" @click="load">重试</button>
		</p>
		<p v-else-if="loading" role="status" class="empty-state">正在加载…</p>
		<template v-else>
			<div v-if="!items.length" class="empty-state">
				<span class="lucide-folder-open text-3xl text-ink-gray-4" />
				<h2>{{ filtered ? '没有找到匹配的作品' : '还没有作品' }}</h2>
				<p>
					{{
						filtered
							? '试试其他关键词或语言筛选。'
							: '从一个想法开始，保存你的第一个代码作品。'
					}}
				</p>
				<button v-if="filtered" class="empty-action" @click="resetFilters">
					清除筛选</button
				><RouterLink v-else :to="{ name: 'Creation' }" class="empty-action"
					>新建作品 →</RouterLink
				>
			</div>
			<div v-else class="creation-grid">
				<article v-for="item in items" :key="item.name" class="creation-card">
					<div class="card-heading">
						<RouterLink :to="creationRoute(item)" class="card-title"
							><h2>{{ item.title }}</h2></RouterLink
						>
						<details class="card-menu">
							<summary :aria-label="`${item.title}的更多操作`">
								<span class="lucide-ellipsis size-5" />
							</summary>
							<div class="menu-options">
								<button @click="openAction('rename', item, $event)">
									<span class="lucide-pencil size-4" />重命名</button
								><button
									class="text-ink-red-4"
									@click="openAction('delete', item, $event)"
								>
									<span class="lucide-trash-2 size-4" />删除
								</button>
							</div>
						</details>
					</div>
					<span class="language-badge">{{ item.language }}</span>
					<div class="card-footer">
						<time
							:datetime="item.modified.replace(' ', 'T')"
							:title="`更新于 ${item.modified}`"
							>{{ formatModified(item.modified) }}</time
						><RouterLink :to="creationRoute(item)" class="continue-link"
							>继续编辑 <span class="lucide-arrow-right size-4"
						/></RouterLink>
					</div>
				</article>
			</div>
			<footer v-if="total" class="list-footer">
				<span
					>显示 {{ page * 20 + 1 }}–{{ page * 20 + items.length }}，共
					{{ total }} 个作品</span
				>
				<nav aria-label="作品分页">
					<button
						:disabled="page === 0"
						aria-label="上一页"
						@click="changePage(page - 1)"
					>
						<span class="lucide-chevron-left size-4" /></button
					><button
						v-for="number in visiblePages"
						:key="number"
						:class="{ current: page === number - 1 }"
						:aria-current="page === number - 1 ? 'page' : undefined"
						:aria-label="`第 ${number} 页`"
						@click="changePage(number - 1)"
					>
						{{ number }}</button
					><button
						:disabled="page + 1 >= pageCount"
						aria-label="下一页"
						@click="changePage(page + 1)"
					>
						<span class="lucide-chevron-right size-4" />
					</button>
				</nav>
			</footer>
		</template>
		<Dialog
			v-model:open="dialogOpen"
			:title="action === 'rename' ? '重命名作品' : '删除作品'"
		>
			<template #default
				><form id="creation-action" @submit.prevent="confirmAction">
					<label v-if="action === 'rename'" class="rename-field"
						>作品名称<input
							v-model="newTitle"
							aria-label="新的作品名称"
							maxlength="140"
							:disabled="busy"
					/></label>
					<p v-else class="text-sm leading-6 text-ink-gray-7">
						确定删除「{{ selected?.title }}」？删除后无法恢复。
					</p>
					<p
						v-if="actionError"
						role="alert"
						class="mt-3 text-sm text-ink-red-4"
					>
						{{ actionError }}
					</p>
				</form></template
			>
			<template #actions
				><Button :disabled="busy" @click="dialogOpen = false">取消</Button
				><Button
					:theme="action === 'delete' ? 'red' : 'gray'"
					variant="solid"
					:loading="busy"
					:disabled="busy || (action === 'rename' && !newTitle.trim())"
					@click="confirmAction"
					>{{ action === 'rename' ? '保存名称' : '确认删除' }}</Button
				></template
			>
		</Dialog>
	</div>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Button, Dialog, call } from 'frappe-ui'
interface Creation {
	name: string
	title: string
	language: string
	modified: string
}
const languages = [
	{ label: '全部', value: '' },
	{ label: 'Python', value: 'Python' },
	{ label: 'C++', value: 'C++' },
]
const query = ref('')
const activeQuery = ref('')
const language = ref('')
const sort = ref('modified')
const page = ref(0)
const loading = ref(false)
const error = ref('')
const total = ref(0)
const items = ref<Creation[]>([])
const filtered = computed(() => !!activeQuery.value || !!language.value)
const pageCount = computed(() => Math.ceil(total.value / 20))
const visiblePages = computed(() => {
	const start = Math.max(1, Math.min(page.value - 1, pageCount.value - 4))
	return Array.from(
		{ length: Math.min(5, pageCount.value) },
		(_, i) => start + i,
	)
})
const dialogOpen = ref(false)
const selected = ref<Creation | null>(null)
const action = ref<'rename' | 'delete'>('rename')
const newTitle = ref('')
const busy = ref(false)
const actionError = ref('')
let generation = 0
let alive = true
const creationRoute = (item: Creation) => ({
	name: 'CreationDetail',
	params: { creationId: item.name },
})
function formatModified(value: string) {
	const date = new Date(value.replace(' ', 'T'))
	if (Number.isNaN(date.getTime())) return value
	return date.toLocaleString('zh-CN', {
		year: 'numeric',
		month: '2-digit',
		day: '2-digit',
		hour: '2-digit',
		minute: '2-digit',
		hour12: false,
	})
}
async function load() {
	const current = ++generation
	loading.value = true
	error.value = ''
	try {
		const data = await call('lms.lms.creation.get_creations', {
			start: page.value * 20,
			search: activeQuery.value,
			language: language.value,
			sort: sort.value,
			with_total: true,
		})
		if (current !== generation) return
		total.value = data.total
		if (page.value > 0 && page.value >= pageCount.value) {
			page.value = Math.max(0, pageCount.value - 1)
			return await load()
		}
		items.value = data.items
	} catch (e: any) {
		if (current === generation)
			error.value = e.messages?.[0] || e.message || '作品加载失败。'
	} finally {
		if (current === generation) loading.value = false
	}
}
function changePage(value: number) {
	if (value < 0 || value >= pageCount.value || loading.value) return
	page.value = value
	load()
}
function search() {
	activeQuery.value = query.value.trim()
	page.value = 0
	load()
}
function filterLanguage(value: string) {
	language.value = value
	search()
}
function clearSearch() {
	query.value = ''
	search()
}
function resetFilters() {
	query.value = ''
	language.value = ''
	search()
}
function openAction(value: 'rename' | 'delete', item: Creation, event: Event) {
	if (busy.value) return
	;(event.currentTarget as HTMLElement)
		.closest('details')
		?.removeAttribute('open')
	action.value = value
	selected.value = item
	newTitle.value = item.title
	actionError.value = ''
	dialogOpen.value = true
}
async function confirmAction() {
	if (busy.value || !selected.value) return
	busy.value = true
	actionError.value = ''
	try {
		await call(
			`lms.lms.creation.${action.value === 'rename' ? 'rename_creation' : 'delete_creation'}`,
			{
				name: selected.value.name,
				modified: selected.value.modified,
				...(action.value === 'rename' ? { title: newTitle.value } : {}),
			},
		)
		if (!alive) return
		dialogOpen.value = false
		await load()
	} catch (e: any) {
		if (alive)
			actionError.value = e.messages?.[0] || e.message || '操作失败，请重试。'
	} finally {
		busy.value = false
	}
}
onMounted(load)
onBeforeUnmount(() => {
	generation++
	alive = false
})
</script>
<style scoped>
.creations-page {
	width: 100%;
	max-width: 1500px;
	margin: 0 auto;
	padding: 32px 40px;
	color: var(--ink-gray-9);
}
.breadcrumb {
	display: flex;
	gap: 12px;
	font-size: 13px;
	color: var(--ink-gray-5);
	margin-bottom: 20px;
}
.page-heading {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 20px;
}
.page-heading h1 {
	font-size: 30px;
	font-weight: 650;
	line-height: 1.3;
}
.page-heading p {
	color: var(--ink-gray-6);
	margin-top: 10px;
	font-size: 15px;
}
.new-creation {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 8px;
	flex-shrink: 0;
	padding: 11px 18px;
	border-radius: 8px;
	background: #15803d;
	color: white;
	font-size: 14px;
	font-weight: 550;
}
.new-creation:hover {
	background: #166534;
}
.creation-count {
	margin: 28px 0 12px;
	font-size: 14px;
	color: var(--ink-gray-6);
}
.filter-bar {
	display: flex;
	align-items: center;
	gap: 16px;
	margin-bottom: 24px;
}
.search-field {
	display: flex;
	align-items: center;
	flex: 1;
	min-width: 160px;
	border: 1px solid var(--outline-gray-2);
	border-radius: 8px;
	padding: 0 10px;
	background: var(--surface-base);
}
.search-field:focus-within {
	border-color: #15803d;
}
.search-field button {
	display: flex;
	align-items: center;
	justify-content: center;
	color: var(--ink-gray-5);
	width: 28px;
	height: 40px;
	flex-shrink: 0;
}
.search-field input {
	width: 100%;
	min-width: 0;
	border: 0;
	background: transparent;
	font-size: 14px;
	box-shadow: none;
}
.language-filter {
	display: flex;
	flex-shrink: 0;
	padding: 4px;
	border: 1px solid var(--outline-gray-2);
	border-radius: 8px;
	background: var(--surface-gray-1);
}
.language-filter button {
	padding: 7px 18px;
	font-size: 13px;
	border-radius: 5px;
	color: var(--ink-gray-6);
}
.language-filter .selected {
	background: #e2f3e9;
	color: #166534;
	font-weight: 600;
}
.sort-field select {
	min-width: 144px;
	border: 1px solid var(--outline-gray-2);
	border-radius: 8px;
	height: 42px;
	font-size: 14px;
	background-color: var(--surface-base);
}
.creation-grid {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 20px;
}
.creation-card {
	display: flex;
	flex-direction: column;
	min-width: 0;
	padding: 22px 20px 18px;
	border: 1px solid var(--outline-gray-2);
	border-radius: 10px;
	background: var(--surface-base);
	transition: border-color 0.15s;
}
.creation-card:hover,
.creation-card:focus-within {
	border-color: #15803d;
}
.card-heading {
	display: flex;
	align-items: flex-start;
	gap: 10px;
}
.card-title {
	min-width: 0;
	flex: 1;
}
.card-title h2 {
	font-size: 17px;
	line-height: 1.5;
	font-weight: 600;
	overflow-wrap: anywhere;
}
.card-menu {
	position: relative;
	flex-shrink: 0;
}
.card-menu summary {
	list-style: none;
	cursor: pointer;
	color: var(--ink-gray-5);
	padding: 3px;
	border-radius: 4px;
}
.card-menu summary::-webkit-details-marker {
	display: none;
}
.menu-options {
	position: absolute;
	top: 32px;
	right: 0;
	width: 130px;
	padding: 5px;
	z-index: 5;
	border: 1px solid var(--outline-gray-2);
	border-radius: 8px;
	background: var(--surface-base);
	box-shadow: 0 4px 16px #00000012;
}
.menu-options button {
	display: flex;
	align-items: center;
	gap: 8px;
	width: 100%;
	padding: 9px;
	border-radius: 4px;
	font-size: 13px;
	text-align: left;
}
.menu-options button:hover {
	background: var(--surface-gray-2);
}
.language-badge {
	align-self: flex-start;
	margin-top: 14px;
	padding: 3px 9px;
	font-size: 12px;
	border: 1px solid var(--outline-gray-2);
	border-radius: 12px;
	background: var(--surface-gray-1);
}
.card-footer {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	padding-top: 26px;
	margin-top: auto;
}
.card-footer time {
	font-size: 12px;
	color: var(--ink-gray-5);
}
.continue-link {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	flex-shrink: 0;
	font-size: 13px;
	font-weight: 550;
	color: #15803d;
}
.list-footer {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 16px;
	margin-top: 26px;
	font-size: 13px;
	color: var(--ink-gray-6);
}
.list-footer nav {
	display: flex;
	gap: 8px;
}
.list-footer button {
	display: flex;
	align-items: center;
	justify-content: center;
	min-width: 34px;
	height: 34px;
	border: 1px solid var(--outline-gray-2);
	border-radius: 7px;
}
.list-footer button.current {
	background: #15803d;
	border-color: #15803d;
	color: white;
}
.list-footer button:disabled {
	opacity: 0.4;
	cursor: not-allowed;
}
.empty-state {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 12px;
	padding: 72px 16px;
	text-align: center;
	color: var(--ink-gray-6);
	font-size: 14px;
}
.empty-state h2 {
	font-size: 18px;
	font-weight: 600;
	color: var(--ink-gray-8);
}
.empty-action {
	margin-top: 8px;
	color: #15803d;
}
.notice {
	margin: 28px 0;
	font-size: 14px;
}
.rename-field {
	display: flex;
	flex-direction: column;
	gap: 8px;
	font-size: 14px;
}
.rename-field input {
	border: 1px solid var(--outline-gray-2);
	border-radius: 6px;
	background: var(--surface-base);
}
button:focus-visible,
a:focus-visible,
summary:focus-visible {
	outline: 2px solid #15803d;
	outline-offset: 3px;
}
@media (max-width: 1200px) {
	.creations-page {
		padding: 28px 24px;
	}
	.creation-grid {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
	.filter-bar {
		flex-wrap: wrap;
	}
	.search-field {
		flex-basis: 100%;
	}
	.sort-field {
		margin-left: auto;
	}
}
@media (max-width: 640px) {
	.creations-page {
		padding: 24px 16px;
	}
	.page-heading {
		align-items: flex-start;
		flex-wrap: wrap;
		gap: 16px;
	}
	.page-heading h1 {
		font-size: 26px;
	}
	.page-heading p {
		font-size: 13px;
	}
	.creation-grid {
		grid-template-columns: minmax(0, 1fr);
		gap: 14px;
	}
	.language-filter {
		flex: 1;
	}
	.language-filter button {
		flex: 1;
		padding: 7px 10px;
	}
	.sort-field select {
		min-width: 120px;
		width: 120px;
	}
	.filter-bar {
		gap: 10px;
	}
	.list-footer {
		flex-wrap: wrap;
	}
	.list-footer nav {
		margin-left: auto;
	}
}
</style>
