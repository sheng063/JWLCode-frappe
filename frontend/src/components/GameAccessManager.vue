<template>
	<div class="access-manager">
		<section class="rules-card" aria-labelledby="access-rules-title">
			<header class="rules-heading">
				<div class="section-title">
					<ShieldCheck />
					<h2 id="access-rules-title">全站解锁规则</h2>
					<span class="admin-label">{{
						options.can_configure ? '管理员可配置' : '全站规则'
					}}</span>
				</div>
				<span class="entrance-badge" :class="{ closed: !settings.enabled }"
					><span />{{
						settings.enabled ? '学生入口已开放' : '学生入口已关闭'
					}}</span
				>
			</header>
			<form
				v-if="options.can_configure"
				class="rules-form"
				@submit.prevent="saveRule"
			>
				<label class="course-toggle"
					><span>完成学习后解锁</span
					><input
						v-model="required"
						type="checkbox"
						role="switch"
						:disabled="busy" /><span class="toggle-track" aria-hidden="true"
				/></label>
				<label class="default-course"
					><span>默认解锁课程</span>
					<div>
						<select
							v-model="defaultCourse"
							class="access-field"
							:disabled="busy"
							aria-label="默认解锁课程"
							@change="defaultLesson = ''"
						>
							<option value="">请选择课程</option>
							<option
								v-if="
									defaultCourse &&
									!options.courses.some((c) => c.name === defaultCourse)
								"
								:value="defaultCourse"
							>
								{{ defaultCourse }}
							</option>
							<option
								v-for="c in options.courses"
								:key="c.name"
								:value="c.name"
							>
								{{ c.title }}
							</option>
						</select>
						<p class="hint">学生未单独指定规则时，使用此默认课程和解锁条件。</p>
					</div></label
				>
				<GameUnlockCondition
					v-model="defaultLesson"
					:course="defaultCourse"
					label="默认解锁条件"
					:disabled="busy"
				/>
				<button
					class="access-button primary"
					type="submit"
					:disabled="busy || (required && !defaultCourse)"
				>
					保存全站规则
				</button>
			</form>
			<div v-else class="rule-readonly">
				<p>
					{{
						settings.require_course_completion
							? settings.default_required_lesson
								? '完成指定课时后自动解锁'
								: '完成指定课程后自动解锁'
							: '无需完成课程即可解锁'
					}}
				</p>
				<p class="hint">
					默认课程：{{ defaultCourseTitle }} · {{ defaultConditionTitle }} ·
					全站规则由管理员配置。
				</p>
			</div>
		</section>
		<p class="policy-note">
			<Info /><span>单独放行仍受全站开关控制；禁止进入优先于课程完成。</span>
		</p>
		<div v-if="error && !editing" class="message error" role="alert">
			{{ error
			}}<button class="text-button" :disabled="busy" @click="initialize">
				重新加载
			</button>
		</div>
		<p v-if="notice" class="message success" role="status">{{ notice }}</p>
		<section
			class="students-card"
			aria-labelledby="students-title"
			:aria-busy="busy"
		>
			<header class="students-toolbar">
				<div class="student-heading">
					<h2 id="students-title">学生访问管理</h2>
					<span class="hint">共 {{ total }} 名学生</span>
				</div>
				<form class="filters" @submit.prevent="load(0)">
					<label class="student-search"
						><Search /><input
							v-model="search"
							type="search"
							aria-label="学生姓名或账号"
							placeholder="搜索学生姓名或账号…"
							:disabled="busy" /></label
					><select
						v-model="batch"
						class="access-field"
						aria-label="班级"
						:disabled="busy"
					>
						<option value="">全部班级</option>
						<option v-for="b in options.batches" :key="b.name" :value="b.name">
							{{ b.title }}
						</option></select
					><select
						v-model="course"
						class="access-field"
						aria-label="筛选解锁课程"
						:disabled="busy"
					>
						<option value="">全部课程</option>
						<option v-for="c in options.courses" :key="c.name" :value="c.name">
							{{ c.title }}
						</option></select
					><select
						v-model="status"
						class="access-field"
						aria-label="访问状态"
						:disabled="busy"
					>
						<option value="">全部状态</option>
						<option value="unlocked">已解锁</option>
						<option value="locked">未解锁</option></select
					><button type="submit" class="access-button" :disabled="busy">
						{{ busy ? '加载中…' : '查询' }}
					</button>
				</form>
			</header>
			<div v-if="selected.length" class="bulk-bar">
				<span class="selected-label"
					><Check />已选 {{ selected.length }} 人</span
				><select
					v-model="bulkCourse"
					aria-label="批量指定课程"
					@change="bulkLesson = ''"
					class="access-field"
					:disabled="busy"
				>
					<option value="">选择解锁课程</option>
					<option v-for="c in options.courses" :key="c.name" :value="c.name">
						{{ c.title }}
					</option></select
				><GameUnlockCondition
					v-model="bulkLesson"
					:course="bulkCourse"
					label="批量解锁条件"
					:disabled="busy"
				/><button
					class="access-button accent"
					:disabled="busy || !bulkCourse"
					@click="bulk('assign_course')"
				>
					批量指定课程</button
				><button class="text-button" :disabled="busy" @click="bulk('reset')">
					恢复默认自动规则</button
				><button
					class="text-button clear-selection"
					:disabled="busy"
					@click="selected = []"
				>
					取消选择
				</button>
			</div>
			<div class="table-scroll">
				<table class="students-table">
					<thead>
						<tr>
							<th class="check-cell">
								<input
									type="checkbox"
									aria-label="选择本页学生"
									:checked="rows.length > 0 && selected.length === rows.length"
									:indeterminate="
										selected.length > 0 && selected.length < rows.length
									"
									:disabled="busy || !rows.length"
									@change="selectPage"
								/>
							</th>
							<th>学生</th>
							<th>解锁课程 / 进度</th>
							<th>访问模式</th>
							<th>访问状态</th>
							<th class="action-cell">操作</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="row in rows"
							:key="row.student"
							:class="{ selected: selected.includes(row.student) }"
						>
							<td class="check-cell">
								<input
									v-model="selected"
									type="checkbox"
									:value="row.student"
									:aria-label="`选择 ${row.full_name}`"
									:disabled="busy"
								/>
							</td>
							<td>
								<div class="student-identity">
									<span class="student-avatar" aria-hidden="true">{{
										(row.full_name || row.student).slice(0, 1)
									}}</span>
									<div>
										<strong>{{ row.full_name }}</strong>
										<p class="student-email">{{ row.student }}</p>
									</div>
								</div>
							</td>
							<td class="course-cell">
								<div class="course-name">
									{{ row.course_title || '未配置课程'
									}}<span v-if="row.required_course" class="course-origin">{{
										row.course_override ? '单独指定' : '默认'
									}}</span>
								</div>
								<p class="hint">
									{{
										row.required_lesson
											? `指定课时：${row.lesson_title || '课时已不可用'}`
											: '整门课程完成后解锁'
									}}
								</p>
								<div class="progress-line">
									<div
										class="progress-track"
										role="progressbar"
										:aria-label="`${row.full_name} 的课时完成进度`"
										:aria-valuenow="row.completed_lessons"
										:aria-valuemin="0"
										:aria-valuemax="row.total_lessons || 1"
									>
										<span :style="{ width: `${progress(row)}%` }" />
									</div>
									<span
										>{{ row.completed_lessons }} /
										{{ row.total_lessons }} 课时</span
									>
								</div>
							</td>
							<td>
								<span
									class="mode-label"
									:class="row.access_mode.toLowerCase()"
									>{{ modeLabels[row.access_mode] }}</span
								>
							</td>
							<td class="state-cell">
								<span class="status-badge" :class="statusClass(row)">{{
									row.can_enter ? '已解锁' : '未解锁'
								}}</span>
								<p class="hint">{{ row.message }}</p>
							</td>
							<td class="action-cell">
								<button
									class="access-button settings-button"
									:disabled="busy"
									@click="openStudent(row)"
								>
									<Settings2 />设置
								</button>
							</td>
						</tr>
					</tbody>
				</table>
				<div v-if="!rows.length" class="empty-students">
					<Users />
					<p>{{ busy ? '正在加载学生…' : '没有符合条件的学生' }}</p>
					<span v-if="!busy" class="hint">请调整筛选条件后重试。</span>
				</div>
			</div>
			<footer class="table-footer">
				<span>共 {{ total }} 人 · 第 {{ Math.floor(start / 20) + 1 }} 页</span>
				<div>
					<button
						class="access-button"
						:disabled="busy || start === 0"
						@click="load(start - 20)"
					>
						<ChevronLeft />上一页</button
					><button
						class="access-button"
						:disabled="busy || start + 20 >= total"
						@click="load(start + 20)"
					>
						下一页<ChevronRight />
					</button>
				</div>
			</footer>
		</section>
		<Dialog :open="!!editing" class="student-dialog" @close="closeStudent">
			<div class="drawer-backdrop" aria-hidden="true" />
			<div class="drawer-position">
				<DialogPanel v-if="editing" class="student-drawer"
					><header class="drawer-heading">
						<div>
							<DialogTitle class="drawer-title">学生访问设置</DialogTitle
							><DialogDescription class="drawer-description"
								>为这名学生单独设置游戏解锁方式。</DialogDescription
							>
						</div>
						<button
							class="drawer-close"
							aria-label="关闭学生设置"
							:disabled="busy"
							@click="closeStudent"
						>
							<X />
						</button>
					</header>
					<form
						id="student-access-form"
						class="drawer-body"
						@submit.prevent="saveStudent"
					>
						<div class="student-summary">
							<div class="summary-heading">
								<div class="student-identity">
									<span class="student-avatar">{{
										(currentStudent.full_name || currentStudent.student).slice(
											0,
											1,
										)
									}}</span>
									<div>
										<strong>{{ currentStudent.full_name }}</strong>
										<p class="student-email">{{ currentStudent.student }}</p>
									</div>
								</div>
								<span
									class="status-badge"
									:class="statusClass(currentStudent)"
									>{{
										currentStudent.can_enter ? '当前已解锁' : '当前未解锁'
									}}</span
								>
							</div>
							<div class="summary-progress">
								<div>
									<strong>{{
										currentStudent.course_title || '未配置课程'
									}}</strong
									><span
										>{{ currentStudent.completed_lessons }} /
										{{ currentStudent.total_lessons }} 课时</span
									>
								</div>
								<div class="progress-track">
									<span :style="{ width: `${progress(currentStudent)}%` }" />
								</div>
								<p class="hint">
									{{
										currentStudent.required_lesson
											? `指定课时：${currentStudent.lesson_title || '课时已不可用'}`
											: '整门课程完成后解锁'
									}}
								</p>
								<p class="hint">当前状态：{{ currentStudent.message }}</p>
							</div>
						</div>
						<fieldset class="mode-options" :disabled="busy">
							<legend>访问模式</legend>
							<label
								v-for="(label, value) in modeLabels"
								:key="value"
								class="mode-option"
								:class="{
									chosen: editing.access_mode === value,
									'deny-option': value === 'Deny',
								}"
								><input
									v-model="editing.access_mode"
									type="radio"
									name="student-access-mode"
									:value="value"
								/><component :is="modeIcons[value]" /><span
									><strong>{{ label }}</strong
									><small>{{ modeDescriptions[value] }}</small></span
								></label
							>
						</fieldset>
						<label class="drawer-field"
							><span>解锁课程</span
							><select
								v-model="editing.course_override"
								class="access-field"
								:disabled="busy"
								aria-label="学生解锁课程"
								@change="editing.lesson_override = ''"
							>
								<option value="">
									继承默认规则 · {{ defaultCourseTitle }}
								</option>
								<option
									v-if="
										editing.course_override &&
										!options.courses.some(
											(c) => c.name === editing.course_override,
										)
									"
									:value="editing.course_override"
								>
									{{ currentStudent.course_title }}（其他教师指定）
								</option>
								<option
									v-for="c in options.courses"
									:key="c.name"
									:value="c.name"
								>
									{{ c.title }}
								</option></select
							><small class="hint"
								>留空时继承全站默认课程和解锁条件，也可以为该生单独指定。</small
							></label
						>
						<GameUnlockCondition
							v-if="editing.course_override"
							v-model="editing.lesson_override"
							:course="editing.course_override"
							label="学生解锁条件"
							:disabled="busy"
						/>
						<p v-else class="hint">
							继承默认解锁条件：{{ defaultConditionTitle }}
						</p>
						<label class="drawer-field"
							><span>教师备注 <span class="optional-label">选填</span></span>
							<div class="reason-input">
								<textarea
									v-model="editing.reason"
									maxlength="500"
									rows="3"
									:disabled="busy"
									placeholder="记录调整原因，便于后续查看…"
								/><span>{{ editing.reason.length }} / 500</span>
							</div>
							<small class="hint">仅供教师审计。</small></label
						>
						<p class="policy-note drawer-policy">
							<Info /><span
								>全站关闭时，单独放行也无法进入游戏。<small
									>禁止进入优先于课程完成。</small
								></span
							>
						</p>
						<p v-if="currentStudent.modified" class="audit-line">
							<Clock />最近修改：{{ currentStudent.modified_by }} ·
							{{ currentStudent.modified }}
						</p>
						<p v-if="error" class="message error" role="alert">{{ error }}</p>
					</form>
					<footer class="drawer-footer">
						<span>仅对当前学生生效</span>
						<div>
							<button
								class="access-button"
								:disabled="busy"
								@click="closeStudent"
							>
								取消</button
							><button
								class="access-button primary"
								type="submit"
								form="student-access-form"
								:disabled="busy"
							>
								{{ busy ? '正在保存…' : '保存学生设置' }}
							</button>
						</div>
					</footer>
				</DialogPanel>
			</div>
		</Dialog>
	</div>
</template>
<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import GameUnlockCondition from '@/components/GameUnlockCondition.vue'
import { call } from 'frappe-ui'
import {
	Dialog,
	DialogPanel,
	DialogTitle,
	DialogDescription,
} from '@headlessui/vue'
import {
	ShieldCheck,
	Info,
	Search,
	Settings2,
	ChevronLeft,
	ChevronRight,
	Check,
	BookOpen,
	Unlock,
	Lock,
	X,
	Clock,
	Users,
} from 'lucide-vue-next'
const props = defineProps({ settings: { type: Object, required: true } })
const emit = defineEmits(['changed'])
const options = ref({ courses: [], batches: [], can_configure: false })
const required = ref(false),
	defaultCourse = ref(''),
	defaultLesson = ref(''),
	search = ref(''),
	batch = ref(''),
	course = ref(''),
	status = ref('')
const rows = ref([]),
	total = ref(0),
	start = ref(0),
	selected = ref([]),
	bulkCourse = ref(''),
	bulkLesson = ref(''),
	editing = ref(null)
const busy = ref(false),
	error = ref(''),
	notice = ref('')
const currentStudent = ref(null)
const defaultCourseTitle = computed(
	() =>
		options.value.courses.find(
			(c) => c.name === props.settings.default_required_course,
		)?.title ||
		props.settings.default_required_course ||
		'未配置默认课程',
)
const defaultConditionTitle = computed(() =>
	props.settings.default_required_lesson
		? `指定课时：${props.settings.default_lesson_title || props.settings.default_required_lesson}`
		: '整门课程完成后解锁',
)
const modeDescriptions = {
	Automatic: '完成整门课程或指定课时后，自动获得访问权限。',
	Allow: '无需完成课程，允许该学生进入游戏。',
	Deny: '无论课程是否完成，都不允许该学生进入游戏。',
}
const modeIcons = { Automatic: BookOpen, Allow: Unlock, Deny: Lock }
function progress(row) {
	return row.total_lessons > 0
		? Math.min(
				100,
				Math.max(0, (row.completed_lessons / row.total_lessons) * 100),
			)
		: 0
}
function statusClass(row) {
	return row.can_enter
		? 'unlocked'
		: ['denied', 'disabled_user'].includes(row.reason_code)
			? 'denied'
			: 'locked'
}
function openStudent(row) {
	if (busy.value) return
	error.value = ''
	currentStudent.value = { ...row }
	editing.value = {
		...row,
		reason: row.reason || '',
		course_override: row.course_override || '',
		lesson_override: row.lesson_override || '',
	}
}
function closeStudent() {
	if (!busy.value) editing.value = null
}
function selectPage(event) {
	selected.value = event.target.checked
		? rows.value.map((row) => row.student)
		: []
}
const modeLabels = {
	Automatic: '按课程自动解锁',
	Allow: '单独放行',
	Deny: '禁止进入',
}
watch(
	[
		() => props.settings.require_course_completion,
		() => props.settings.default_required_course,
		() => props.settings.default_required_lesson,
	],
	([requiresCourse, courseName, lessonName]) => {
		required.value = !!requiresCourse
		defaultCourse.value = courseName || ''
		defaultLesson.value = lessonName || ''
	},
	{ immediate: true },
)
function fail(err) {
	error.value = err?.messages?.[0] || '操作失败，请重试。'
}
async function load(offset = start.value) {
	busy.value = true
	error.value = ''
	try {
		const result = await call('lms.lms.game_access.get_students', {
			search: search.value,
			batch: batch.value,
			course: course.value,
			status: status.value,
			start: offset,
		})
		rows.value = result.rows
		total.value = result.total
		start.value = offset
		selected.value = []
	} catch (err) {
		fail(err)
	} finally {
		busy.value = false
	}
}
async function saveRule() {
	if (busy.value || !options.value.can_configure) return
	busy.value = true
	error.value = ''
	notice.value = ''
	try {
		await call('lms.lms.game_access.set_course_rule', {
			required: Number(required.value),
			course: defaultCourse.value,
			lesson: defaultLesson.value,
		})
		notice.value = '全站课程解锁规则已保存。'
		emit('changed')
		await load(0)
	} catch (err) {
		fail(err)
	} finally {
		busy.value = false
	}
}
async function saveStudent() {
	if (busy.value || !editing.value) return
	busy.value = true
	error.value = ''
	notice.value = ''
	try {
		const row = editing.value
		await call('lms.lms.game_access.save_student_access', {
			student: row.student,
			required_course: row.course_override,
			required_lesson: row.course_override ? row.lesson_override : '',
			access_mode: row.access_mode,
			reason: row.reason,
		})
		editing.value = null
		notice.value = '学生设置已保存。'
		await load()
	} catch (err) {
		fail(err)
	} finally {
		busy.value = false
	}
}
async function bulk(action) {
	if (
		busy.value ||
		!selected.value.length ||
		(action === 'assign_course' && !bulkCourse.value)
	)
		return
	busy.value = true
	error.value = ''
	notice.value = ''
	try {
		const result = await call('lms.lms.game_access.bulk_student_access', {
			students: selected.value,
			action,
			required_course: action === 'assign_course' ? bulkCourse.value : '',
			required_lesson: action === 'assign_course' ? bulkLesson.value : '',
		})
		notice.value = `已更新 ${result.updated} 名学生。`
		await load()
	} catch (err) {
		fail(err)
	} finally {
		busy.value = false
	}
}
async function initialize() {
	busy.value = true
	error.value = ''
	try {
		options.value = await call('lms.lms.game_access.get_access_options')
		await load(0)
	} catch (err) {
		fail(err)
	} finally {
		busy.value = false
	}
}
onMounted(initialize)
</script>
<style scoped>
.access-manager,
.student-dialog,
.student-drawer {
	--access-accent: #087f68;
	--access-border: #e1e8e6;
	--access-muted: #748291;
	color: #182b28;
	font-size: 14px;
}
.access-manager {
	display: grid;
	gap: 16px;
	min-width: 0;
}
.rules-card,
.students-card {
	border: 1px solid var(--access-border);
	border-radius: 12px;
	background: white;
	min-width: 0;
}
.rules-card {
	padding: 22px;
}
.rules-heading,
.section-title,
.students-toolbar,
.student-heading,
.table-footer,
.summary-heading,
.drawer-heading,
.drawer-footer {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16px;
}
.section-title {
	justify-content: flex-start;
	gap: 12px;
	flex-wrap: wrap;
}
.section-title > svg {
	color: var(--access-accent);
	width: 23px;
	height: 23px;
	flex-shrink: 0;
}
.section-title h2,
.student-heading h2 {
	font-size: 16px;
	font-weight: 650;
}
.admin-label,
.optional-label {
	font-size: 11px;
	background: #f0f3f5;
	color: #71808f;
	padding: 4px 9px;
	border-radius: 15px;
	font-weight: 400;
}
.entrance-badge {
	display: flex;
	align-items: center;
	gap: 7px;
	background: #e8f6ef;
	color: var(--access-accent);
	font-size: 12px;
	padding: 7px 10px;
	border-radius: 20px;
	white-space: nowrap;
}
.entrance-badge > span {
	width: 6px;
	height: 6px;
	background: currentColor;
	border-radius: 50%;
}
.entrance-badge.closed {
	background: #f1f3f5;
	color: #748291;
}
.rules-form {
	flex-wrap: wrap;
	display: flex;
	align-items: center;
	gap: 28px;
	border-top: 1px solid #edf1ef;
	margin-top: 20px;
	padding-top: 20px;
}
.course-toggle {
	position: relative;
	display: flex;
	align-items: center;
	gap: 20px;
	cursor: pointer;
	flex-shrink: 0;
}
.course-toggle input {
	position: absolute;
	right: 0;
	width: 42px;
	height: 24px;
	opacity: 0;
	cursor: pointer;
}
.toggle-track {
	width: 42px;
	height: 24px;
	background: #b8c2c6;
	border-radius: 24px;
	pointer-events: none;
}
.toggle-track:after {
	content: '';
	display: block;
	width: 18px;
	height: 18px;
	border-radius: 50%;
	background: white;
	margin: 3px;
	box-shadow: 0 1px 3px #0002;
	transition: transform 0.15s;
}
.course-toggle input:checked + .toggle-track {
	background: var(--access-accent);
}
.course-toggle input:checked + .toggle-track:after {
	transform: translateX(18px);
}
.course-toggle input:focus-visible + .toggle-track {
	outline: 2px solid var(--access-accent);
	outline-offset: 3px;
}
.default-course {
	display: flex;
	align-items: flex-start;
	gap: 16px;
	flex: 1;
	min-width: 0;
	border-left: 1px solid var(--access-border);
	padding-left: 28px;
}
.default-course > span {
	padding-top: 10px;
	white-space: nowrap;
	font-size: 13px;
}
.default-course > div {
	width: 100%;
	max-width: 390px;
	min-width: 0;
}
.default-course select {
	width: 100%;
}
.hint {
	font-size: 12px;
	line-height: 1.7;
	color: var(--access-muted);
}
.default-course .hint {
	margin-top: 6px;
}
.access-field {
	min-width: 0;
	max-width: 100%;
	border: 1px solid #dbe3e7;
	border-radius: 7px;
	background-color: white;
	font-size: 13px;
	padding: 9px 32px 9px 12px;
	min-height: 38px;
	color: #263a35;
}
.access-button {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 7px;
	min-height: 36px;
	padding: 8px 13px;
	border: 1px solid #d9e3e6;
	border-radius: 7px;
	background: white;
	font-size: 13px;
	font-weight: 500;
	white-space: nowrap;
	transition: background 0.15s;
}
.access-button svg {
	width: 15px;
	height: 15px;
	flex-shrink: 0;
}
.access-button:hover:not(:disabled) {
	background: #eff8f3;
}
.access-button.primary {
	background: var(--access-accent);
	color: white;
	border-color: var(--access-accent);
}
.access-button.primary:hover:not(:disabled) {
	background: #066a57;
}
.access-button.accent {
	border-color: #8abaaa;
	color: var(--access-accent);
}
button:disabled,
select:disabled,
input:disabled,
textarea:disabled {
	opacity: 0.5;
	cursor: not-allowed;
}
button:focus-visible,
input:focus-visible,
select:focus-visible,
textarea:focus-visible {
	outline: 2px solid var(--access-accent);
	outline-offset: 3px;
}
.policy-note {
	display: flex;
	align-items: center;
	gap: 10px;
	padding: 12px 15px;
	background: #e8f6f1;
	border: 1px solid #d8eee5;
	border-radius: 8px;
	color: #087763;
	font-size: 12px;
	line-height: 1.7;
}
.policy-note > svg {
	width: 17px;
	height: 17px;
	flex-shrink: 0;
}
.rule-readonly {
	margin-top: 20px;
	border-top: 1px solid var(--access-border);
	padding-top: 18px;
	line-height: 1.9;
}
.students-toolbar {
	padding: 20px;
	flex-wrap: wrap;
}
.student-heading {
	justify-content: flex-start;
	gap: 12px;
	flex-shrink: 0;
}
.filters {
	display: flex;
	align-items: center;
	gap: 8px;
	flex-wrap: wrap;
}
.student-search {
	display: flex;
	align-items: center;
	gap: 8px;
	border: 1px solid #dbe3e7;
	border-radius: 7px;
	padding: 0 10px;
	min-width: 180px;
	flex: 1;
}
.student-search svg {
	width: 16px;
	height: 16px;
	color: var(--access-muted);
	flex-shrink: 0;
}
.student-search input {
	border: 0;
	box-shadow: none;
	background: transparent;
	font-size: 13px;
	padding: 10px 0;
	width: 100%;
	min-width: 0;
	outline: none;
}
.student-search:focus-within {
	outline: 2px solid var(--access-accent);
	outline-offset: 2px;
}
.filters select {
	max-width: 180px;
}
.bulk-bar {
	display: flex;
	align-items: center;
	gap: 12px;
	flex-wrap: wrap;
	margin: 0 10px 10px;
	padding: 12px 16px;
	border-radius: 8px;
	background: #eaf8f2;
}
.selected-label {
	display: flex;
	align-items: center;
	gap: 10px;
	white-space: nowrap;
	font-size: 13px;
	font-weight: 600;
}
.selected-label svg {
	color: white;
	background: var(--access-accent);
	padding: 3px;
	border-radius: 5px;
	width: 21px;
	height: 21px;
}
.bulk-bar select {
	max-width: 230px;
}
.text-button {
	color: var(--access-accent);
	font-size: 12px;
	font-weight: 500;
	padding: 7px 0;
}
.clear-selection {
	margin-left: auto;
}
.table-scroll {
	overflow-x: auto;
}
.students-table {
	width: 100%;
	border-collapse: collapse;
	text-align: left;
	font-size: 13px;
	min-width: 870px;
}
.students-table th {
	background: #f6f8f9;
	padding: 13px 16px;
	font-size: 12px;
	font-weight: 500;
	color: var(--access-muted);
	white-space: nowrap;
}
.students-table td {
	padding: 16px;
	border-top: 1px solid #edf1ef;
	vertical-align: middle;
}
.students-table tr.selected {
	background: #edfaf4;
}
.students-table input[type='checkbox'] {
	width: 16px;
	height: 16px;
	accent-color: var(--access-accent);
	color: var(--access-accent);
	border-radius: 4px;
	cursor: pointer;
}
.students-table .check-cell {
	width: 45px;
	padding-right: 6px;
	padding-left: 20px;
}
.student-identity {
	display: flex;
	align-items: center;
	gap: 12px;
	min-width: 0;
}
.student-avatar {
	display: flex;
	align-items: center;
	justify-content: center;
	width: 40px;
	height: 40px;
	border-radius: 50%;
	background: #dcf1e8;
	color: #258b70;
	font-size: 18px;
	flex-shrink: 0;
}
.student-identity strong {
	font-size: 13px;
	font-weight: 600;
}
.student-email {
	font-size: 11px;
	color: var(--access-muted);
	margin-top: 4px;
	overflow-wrap: anywhere;
}
.course-cell {
	min-width: 235px;
	width: 28%;
}
.course-name {
	display: flex;
	align-items: center;
	gap: 8px;
	font-size: 12px;
	flex-wrap: wrap;
}
.course-origin {
	background: #eaf2fc;
	color: #4275aa;
	border-radius: 6px;
	font-size: 10px;
	padding: 3px 7px;
	white-space: nowrap;
}
.progress-line {
	display: flex;
	align-items: center;
	gap: 12px;
	margin-top: 8px;
}
.progress-line > span {
	font-size: 11px;
	color: var(--access-muted);
	white-space: nowrap;
}
.progress-track {
	height: 6px;
	background: #e4e9ed;
	border-radius: 10px;
	overflow: hidden;
	flex: 1;
}
.progress-track > span {
	display: block;
	height: 100%;
	background: var(--access-accent);
	border-radius: inherit;
}
.mode-label {
	white-space: nowrap;
	font-size: 12px;
}
.mode-label.allow,
.mode-label.deny {
	padding: 4px 9px;
	border-radius: 15px;
}
.mode-label.allow {
	background: #e8f0ff;
	color: #4772af;
}
.mode-label.deny {
	background: #ffeaee;
	color: #c45466;
}
.status-badge {
	display: inline-flex;
	padding: 4px 10px;
	border-radius: 20px;
	font-size: 11px;
	font-weight: 600;
	white-space: nowrap;
}
.status-badge.unlocked {
	color: #147e53;
	background: #dff4e8;
}
.status-badge.locked {
	color: #9f6b23;
	background: #fff1d9;
}
.status-badge.denied {
	color: #b7495b;
	background: #ffe7ec;
}
.state-cell {
	min-width: 160px;
	max-width: 225px;
}
.state-cell .hint {
	margin-top: 5px;
	font-size: 11px;
}
.students-table .action-cell {
	text-align: right;
	padding-right: 20px;
}
.settings-button {
	padding: 6px 11px;
	min-height: 32px;
}
.table-footer {
	border-top: 1px solid #edf1ef;
	padding: 16px 20px;
	color: var(--access-muted);
	font-size: 12px;
}
.table-footer > div {
	display: flex;
	gap: 8px;
}
.empty-students {
	padding: 50px 20px;
	text-align: center;
	color: var(--access-muted);
}
.empty-students > svg {
	width: 32px;
	height: 32px;
	margin: 0 auto 12px;
	color: #a2b9af;
}
.empty-students p {
	margin-bottom: 6px;
}
.message {
	padding: 12px 16px;
	border-radius: 8px;
	font-size: 13px;
	line-height: 1.7;
}
.message.error {
	background: #fff0ef;
	color: #aa443a;
}
.message.success {
	background: #e7f5ed;
	color: #237653;
}
.message .text-button {
	margin-left: 15px;
}
.student-dialog {
	position: relative;
	z-index: 70;
}
.drawer-backdrop {
	position: fixed;
	inset: 0;
	background: #17242e66;
}
.drawer-position {
	position: fixed;
	inset: 0;
	display: flex;
	justify-content: flex-end;
	pointer-events: none;
}
.student-drawer {
	pointer-events: auto;
	display: flex;
	flex-direction: column;
	width: min(590px, 100%);
	height: 100%;
	height: 100dvh;
	background: white;
	box-shadow: -10px 0 40px #142b291f;
	outline: none;
}
.drawer-heading {
	padding: 24px 28px 18px;
	align-items: flex-start;
	flex-shrink: 0;
}
.drawer-title {
	font-size: 22px;
	font-weight: 650;
	line-height: 1.4;
}
.drawer-description {
	font-size: 13px;
	line-height: 1.7;
	color: var(--access-muted);
	margin-top: 6px;
}
.drawer-close {
	padding: 4px;
	color: #617280;
	border-radius: 5px;
}
.drawer-close svg {
	width: 20px;
	height: 20px;
}
.drawer-body {
	flex: 1;
	overflow-y: auto;
	overscroll-behavior: contain;
	min-height: 0;
	padding: 0 28px 24px;
	display: flex;
	flex-direction: column;
	gap: 20px;
}
.student-summary {
	background: #f8f9fb;
	border: 1px solid #e1e6eb;
	border-radius: 9px;
	padding: 18px;
}
.summary-heading {
	gap: 12px;
}
.student-summary .student-avatar {
	width: 46px;
	height: 46px;
	background: #eae4ff;
	color: #8165c9;
	font-size: 21px;
}
.student-summary strong {
	font-size: 14px;
}
.summary-progress {
	border-top: 1px solid #e6eaee;
	margin-top: 16px;
	padding-top: 14px;
}
.summary-progress > div:first-child {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
	font-size: 12px;
	color: #4e6070;
}
.summary-progress .progress-track {
	margin: 12px 0 7px;
	height: 8px;
}
.mode-options {
	display: flex;
	flex-direction: column;
	gap: 10px;
	min-width: 0;
}
.mode-options legend,
.drawer-field > span {
	font-size: 14px;
	font-weight: 650;
	margin-bottom: 10px;
}
.mode-option {
	display: flex;
	align-items: center;
	gap: 14px;
	padding: 14px 16px;
	border: 1px solid #dfe6ea;
	border-radius: 8px;
	cursor: pointer;
}
.mode-option.chosen {
	border-color: var(--access-accent);
	background: #f0f9f5;
}
.mode-option input {
	width: 17px;
	height: 17px;
	flex-shrink: 0;
	accent-color: var(--access-accent);
	color: var(--access-accent);
}
.mode-option > svg {
	width: 25px;
	height: 25px;
	flex-shrink: 0;
	color: #607180;
}
.mode-option.chosen > svg {
	color: var(--access-accent);
}
.mode-option.deny-option > svg {
	color: #c85e6b;
}
.mode-option strong {
	display: block;
	font-size: 13px;
	font-weight: 600;
}
.mode-option small {
	display: block;
	font-size: 11px;
	line-height: 1.7;
	color: var(--access-muted);
	margin-top: 4px;
}
.drawer-field {
	display: flex;
	flex-direction: column;
	min-width: 0;
}
.drawer-field .access-field {
	width: 100%;
}
.drawer-field > .hint {
	margin-top: 6px;
}
.drawer-field .optional-label {
	margin-left: 8px;
}
.reason-input {
	position: relative;
	border: 1px solid #dbe3e7;
	border-radius: 8px;
	overflow: hidden;
}
.reason-input textarea {
	display: block;
	width: 100%;
	border: 0;
	border-radius: 8px;
	box-shadow: none;
	padding: 12px 12px 28px;
	font-size: 13px;
	line-height: 1.6;
	resize: vertical;
	min-height: 90px;
}
.reason-input > span {
	position: absolute;
	bottom: 8px;
	right: 12px;
	font-size: 11px;
	color: var(--access-muted);
	pointer-events: none;
}
.reason-input:focus-within {
	outline: 2px solid var(--access-accent);
	outline-offset: 2px;
}
.drawer-policy {
	align-items: flex-start;
	flex-shrink: 0;
}
.drawer-policy > svg {
	margin-top: 2px;
}
.drawer-policy small {
	display: block;
	font-size: 11px;
	color: var(--access-muted);
	margin-top: 4px;
}
.audit-line {
	display: flex;
	align-items: flex-start;
	gap: 8px;
	font-size: 11px;
	color: var(--access-muted);
	line-height: 1.7;
	overflow-wrap: anywhere;
}
.audit-line svg {
	width: 15px;
	height: 15px;
	flex-shrink: 0;
	margin-top: 2px;
}
.drawer-footer {
	padding: 18px 28px;
	padding-bottom: max(18px, env(safe-area-inset-bottom));
	border-top: 1px solid var(--access-border);
	flex-shrink: 0;
	background: white;
}
.drawer-footer > span {
	font-size: 12px;
	color: var(--access-muted);
}
.drawer-footer > div {
	display: flex;
	gap: 10px;
}
.drawer-footer .access-button {
	min-height: 40px;
}
@media (max-width: 1200px) {
	.rules-form {
		gap: 18px;
		flex-wrap: wrap;
	}
	.default-course {
		padding-left: 18px;
	}
	.filters {
		width: 100%;
	}
	.student-search {
		min-width: 230px;
	}
	.filters select {
		flex: 1;
	}
	.rules-heading {
		flex-wrap: wrap;
	}
}
@media (max-width: 700px) {
	.rules-card {
		padding: 18px;
	}
	.rules-form {
		align-items: stretch;
		flex-direction: column;
	}
	.default-course {
		border-left: 0;
		padding-left: 0;
		flex-direction: column;
		gap: 8px;
	}
	.default-course > div {
		max-width: none;
	}
	.default-course > span {
		padding-top: 0;
	}
	.course-toggle {
		justify-content: space-between;
	}
	.section-title {
		gap: 8px;
	}
	.section-title h2 {
		font-size: 15px;
	}
	.students-toolbar {
		padding: 16px;
	}
	.student-search {
		flex-basis: 100%;
		min-width: 0;
	}
	.filters select {
		min-width: 90px;
		max-width: 100%;
	}
	.filters > .access-button {
		width: 100%;
	}
	.bulk-bar {
		gap: 10px;
	}
	.bulk-bar select {
		flex: 1;
		max-width: none;
	}
	.table-footer {
		padding: 14px;
		gap: 12px;
		flex-wrap: wrap;
	}
	.drawer-heading {
		padding: 20px 18px 16px;
	}
	.drawer-body {
		padding: 0 18px 20px;
		gap: 18px;
	}
	.drawer-footer {
		padding: 14px 18px;
		padding-bottom: max(14px, env(safe-area-inset-bottom));
		gap: 8px;
		flex-wrap: wrap;
	}
	.drawer-footer > div {
		margin-left: auto;
	}
	.student-summary {
		padding: 14px;
	}
	.summary-heading {
		flex-wrap: wrap;
	}
	.mode-option {
		padding: 13px 12px;
		gap: 10px;
	}
	.mode-option > svg {
		width: 22px;
		height: 22px;
	}
	.policy-note {
		font-size: 11px;
	}
	.drawer-title {
		font-size: 21px;
	}
}
@media (prefers-reduced-motion: reduce) {
	* {
		transition: none !important;
	}
}
</style>
