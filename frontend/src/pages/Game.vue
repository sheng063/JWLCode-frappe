<template>
	<div class="game-center">
		<div class="breadcrumb">教学空间 <span>/</span> Game</div>
		<div class="page-content">
			<header class="page-heading">
				<div>
					<h1>游戏中心</h1>
					<p>
						{{
							settings?.can_manage
								? '管理课堂游戏，让学习多一点探索。'
								: '选择喜欢的游戏，开始你的探索。'
						}}
					</p>
				</div>
				<div class="heading-actions">
					<button class="control" :disabled="loading" @click="refresh">
						<RefreshCw :class="{ spinning: loading }" />刷新
					</button>
					<button
						v-if="settings?.can_manage"
						class="control primary"
						@click="showUpload = true"
					>
						<Plus />上传游戏
					</button>
				</div>
			</header>
			<p v-if="error && !showUpload" role="alert" class="feedback error">
				{{ error }}
			</p>
			<p v-if="success" role="status" class="feedback success">{{ success }}</p>
			<p v-if="loading && !settings" role="status" class="empty-state">
				正在加载游戏…
			</p>
			<template v-if="settings">
				<nav v-if="settings.can_manage" class="tabs" aria-label="游戏管理导航">
					<button
						:class="{ active: activeTab === 'library' }"
						:aria-current="activeTab === 'library' ? 'page' : undefined"
						@click="activeTab = 'library'"
					>
						游戏库 <span class="count">{{ games.length }}</span>
					</button>
					<button
						:class="{ active: activeTab === 'access' }"
						:aria-current="activeTab === 'access' ? 'page' : undefined"
						@click="activeTab = 'access'"
					>
						学生解锁管理
					</button>
				</nav>
				<div
					v-if="activeTab === 'access' && settings.can_manage"
					class="access-panel"
				>
					<GameAccessManager :settings="settings" @changed="refresh" />
				</div>
				<div
					v-else
					class="workspace"
					:class="{ 'student-workspace': !settings.can_manage }"
				>
					<main class="library">
						<GameAccessNotice v-if="!accessible" :access="settings.access" />
						<template v-else>
							<div class="library-tools">
								<label class="search-box"
									><Search /><input
										v-model="search"
										type="search"
										aria-label="搜索游戏"
										placeholder="搜索游戏名称…"
								/></label>
								<select
									v-model="format"
									class="format-select"
									aria-label="游戏文件格式"
								>
									<option value="">全部格式</option>
									<option value="html">HTML 文件</option>
									<option value="zip">ZIP 游戏包</option>
								</select>
								<div class="view-controls">
									<button
										class="icon-control"
										:class="{ selected: view === 'grid' }"
										aria-label="网格视图"
										:aria-pressed="view === 'grid'"
										@click="view = 'grid'"
									>
										<LayoutGrid /></button
									><button
										class="icon-control"
										:class="{ selected: view === 'list' }"
										aria-label="列表视图"
										:aria-pressed="view === 'list'"
										@click="view = 'list'"
									>
										<List />
									</button>
								</div>
							</div>
							<div
								v-if="filteredGames.length"
								class="game-grid"
								:class="{ 'list-view': view === 'list' }"
							>
								<article
									v-for="(game, index) in filteredGames"
									:key="game.name"
									class="game-card"
								>
									<button class="game-entry" @click="openGame(game)">
										<div class="game-cover" :class="`game-cover-${index % 6}`">
											<img
												v-if="game.cover_image"
												:src="game.cover_image"
												alt=""
												loading="lazy"
												class="game-cover-image"
											/>
											<template v-else
												><span class="cover-orbit" /><span
													class="cover-tile tile-one" /><span
													class="cover-tile tile-two" /><component
													:is="coverIcons[index % 6]"
													class="cover-icon"
											/></template>
											<span class="game-badge">{{
												game.entry_file ? 'ZIP' : 'HTML'
											}}</span>
										</div>
										<div class="game-info">
											<h2>{{ game.title }}</h2>
											<p class="description">
												{{ game.description || '点击进入游戏，开始你的探索。' }}
											</p>
											<p class="filename">{{ game.filename }}</p>
										</div>
									</button>
									<div v-if="settings.can_manage" class="game-availability">
										<label class="visibility-label">
											<span>{{ game.enabled ? '已启用' : '已关闭' }}</span>
											<input
												type="checkbox"
												role="switch"
												:checked="!!game.enabled"
												:disabled="!!busyGame || loading"
												:aria-label="`${game.title} 向学生开放`"
												@change="toggleGameAvailability($event, game)"
											/>
											<span class="switch-track" aria-hidden="true" />
										</label>
									</div>
									<div class="card-actions">
										<button class="control" @click="openGame(game)">
											<Play />{{ settings.can_manage ? '试玩' : '开始游戏' }}
										</button>
										<template v-if="settings.can_manage">
											<button
												class="control"
												:disabled="!!busyGame"
												@click="editGame(game)"
											>
												<Pencil />编辑
											</button>
											<details class="game-menu" @keydown.esc="closeMenu">
												<summary
													class="icon-control"
													:aria-label="`${game.title} 的更多操作`"
												>
													<MoreHorizontal />
												</summary>
												<div class="menu-items">
													<button
														:disabled="!!busyGame"
														@click="runMenuAction($event, game, downloadGame)"
													>
														下载</button
													><button
														class="danger"
														:disabled="!!busyGame"
														@click="runMenuAction($event, game, deleteGame)"
													>
														删除
													</button>
												</div>
											</details>
										</template>
									</div>
									<span
										v-if="busyGame === game.name"
										role="status"
										class="busy-status"
										>处理中…</span
									>
								</article>
							</div>
							<div v-else-if="!loading" class="empty-state">
								<Gamepad2 />
								<h2>
									{{
										games.length
											? '没有找到匹配的游戏'
											: '游戏库等待你的第一份创意'
									}}
								</h2>
								<p>
									{{
										games.length
											? '试试其他关键词，或选择全部格式。'
											: settings.can_manage
												? '上传 HTML 文件或 ZIP 游戏包，开启课堂探索。'
												: '还没有游戏，请等待教师上传。'
									}}
								</p>
								<button
									v-if="games.length"
									class="control"
									@click="clearFilters"
								>
									清除筛选</button
								><button
									v-else-if="settings.can_manage"
									class="control primary"
									@click="showUpload = true"
								>
									<Plus />上传游戏
								</button>
							</div>
							<footer class="library-footer">
								{{
									search || format
										? `找到 ${filteredGames.length} 个游戏 · 共 ${games.length} 个`
										: `共 ${games.length} 个游戏`
								}}
							</footer>
						</template>
					</main>
					<aside
						v-if="settings.can_manage"
						class="settings-rail"
						aria-label="游戏设置"
					>
						<section class="side-card">
							<h2><ShieldCheck />学生访问</h2>
							<label class="visibility-label"
								><span>向学生开放</span
								><input
									type="checkbox"
									role="switch"
									:checked="settings.enabled"
									:disabled="saving"
									aria-label="向学生开放"
									@change="toggleVisibility" /><span
									class="switch-track"
									aria-hidden="true"
							/></label>
							<p class="access-state" :class="{ enabled: settings.enabled }">
								<span />{{
									saving ? '正在保存…' : settings.enabled ? '已开启' : '已关闭'
								}}
							</p>
							<p class="muted">
								对全站学生生效。还需启用对应游戏并满足解锁规则。教师始终可以上传和试玩。
							</p>
							<div class="rule-summary">
								<div class="rule-heading">
									<h3>解锁规则</h3>
									<span class="rule-badge">{{
										settings.require_course_completion
											? settings.default_required_lesson
												? '指定课时完成后解锁'
												: '课程完成后解锁'
											: '无需课程解锁'
									}}</span>
								</div>
								<template v-if="settings.require_course_completion"
									><p class="muted">默认解锁课程</p>
									<div class="course-label">
										<BookOpen />{{ defaultCourseTitle }}
									</div>
									<p class="muted">
										{{
											settings.default_required_lesson
												? `完成指定课时“${settings.default_lesson_title || settings.default_required_lesson}”后自动解锁。`
												: '完成全部课时后自动解锁。'
										}}
									</p></template
								>
								<p v-else class="muted">
									学生可在全站开放后进入，个人禁止规则仍然有效。
								</p>
								<button
									class="control full-width"
									@click="activeTab = 'access'"
								>
									管理学生解锁<ArrowRight />
								</button>
							</div>
							<p class="info-note"><Info />单独放行仍受全站开关控制。</p>
						</section>
						<section class="side-card upload-guide">
							<h2><FileText />上传说明</h2>
							<p>HTML 文件 · 最大 5 MB</p>
							<p>ZIP 游戏包 · 最大 20 MB</p>
							<p class="muted">
								ZIP 需包含入口 HTML 和相关素材，解压后不超过 100 MB。
							</p>
							<button class="text-link" @click="showHelp = true">
								查看说明 <ArrowRight />
							</button>
						</section>
						<section class="classroom-tip">
							<Lightbulb />
							<div>
								<h3>课堂小提示</h3>
								<p>
									先试玩，再向学生开放。通过课程解锁规则，把游戏变成学习后的奖励。
								</p>
							</div>
						</section>
					</aside>
				</div>
			</template>
		</div>
		<Dialog v-model="showUpload" :options="{ title: '上传游戏', size: 'lg' }">
			<template #body-content
				><form
					id="game-upload-form"
					class="upload-form"
					@submit.prevent="upload"
				>
					<p class="muted">把你的课堂创意，变成可以探索的游戏。</p>
					<label
						>游戏名称（选填）<input
							v-model="title"
							:disabled="uploading"
							maxlength="140"
							placeholder="默认使用文件名"
							class="upload-name" /></label
					><label class="file-drop"
						><Upload /><strong>{{
							file ? file.name : '选择 HTML 文件或 ZIP 游戏包'
						}}</strong
						><span>HTML 最大 5 MB · ZIP 最大 20 MB</span
						><input
							ref="fileInput"
							type="file"
							accept=".html,.htm,.zip,text/html,application/zip"
							:disabled="uploading"
							@change="selectFile"
					/></label>
					<p class="muted">
						多文件游戏请打包为 ZIP，并包含 index.html 和相关素材。
					</p>
					<p v-if="error" role="alert" class="feedback error">{{ error }}</p>
				</form></template
			>
			<template #actions
				><Button
					variant="solid"
					:loading="uploading"
					:disabled="!file || uploading"
					@click="upload"
					>{{ uploading ? '正在上传…' : '上传游戏' }}</Button
				><Button :disabled="uploading" @click="showUpload = false"
					>取消</Button
				></template
			>
		</Dialog>
		<Dialog v-model="showHelp" :options="{ title: '游戏上传说明', size: 'lg' }"
			><template #body-content
				><div class="upload-form">
					<p>
						单个 HTML 文件最大 5 MB，使用 UTF-8
						编码；建议将样式、脚本和图片内嵌。
					</p>
					<p>
						多文件游戏请上传 ZIP，最大 20 MB，解压后不超过 100 MB。将 index.html
						和图片、脚本等素材一起打包，使用相对路径引用。
					</p>
					<p>
						上传后可编辑名称、简介和封面，也可通过卡片更多菜单下载原始文件或删除游戏。
					</p>
					<p>
						游戏在隔离环境中运行。请先试玩确认资源和交互正常，再向学生开放。
					</p>
				</div></template
			><template #actions
				><Button @click="showHelp = false">知道了</Button></template
			></Dialog
		>
		<GameEditor
			v-if="editingGame"
			v-model="showEditor"
			:game="editingGame"
			@saved="onEdited"
		/>
	</div>
</template>
<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Button, Dialog, call } from 'frappe-ui'
import { useRouter } from 'vue-router'
import GameEditor from '@/components/GameEditor.vue'
import GameAccessManager from '@/components/GameAccessManager.vue'
import GameAccessNotice from '@/components/GameAccessNotice.vue'
import {
	Gamepad2,
	Play,
	Search,
	LayoutGrid,
	List,
	Plus,
	RefreshCw,
	Pencil,
	MoreHorizontal,
	ShieldCheck,
	FileText,
	Lightbulb,
	Info,
	ArrowRight,
	Upload,
	BookOpen,
	Boxes,
	Rocket,
	Music,
	Flag,
	Shapes,
} from 'lucide-vue-next'
import { useSettings } from '@/stores/settings'
import { readGameFile, saveGameDownload } from '@/utils/game'

const router = useRouter()
const settingsStore = useSettings()
const activeTab = ref('library')
const search = ref('')
const format = ref('')
const view = ref('grid')
const showUpload = ref(false)
const showHelp = ref(false)
const courses = ref([])
const coverIcons = [Gamepad2, Rocket, Shapes, Boxes, Music, Flag]
const filteredGames = computed(() =>
	games.value.filter((game) => {
		const matchesSearch = `${game.title} ${game.filename}`
			.toLocaleLowerCase()
			.includes(search.value.trim().toLocaleLowerCase())
		return (
			matchesSearch &&
			(!format.value || (game.entry_file ? 'zip' : 'html') === format.value)
		)
	}),
)
const defaultCourseTitle = computed(
	() =>
		courses.value.find(
			(course) => course.name === settings.value?.default_required_course,
		)?.title ||
		settings.value?.default_required_course ||
		'未配置默认课程',
)
function openGame(game) {
	router.push({ name: 'GameDetail', params: { gameId: game.name } })
}
function clearFilters() {
	search.value = ''
	format.value = ''
}
function runMenuAction(event, game, action) {
	closeMenu(event)
	action(game)
}
function closeMenu(event) {
	event.currentTarget.closest('details')?.removeAttribute('open')
}
const settings = ref(null)
const games = ref([])
const file = ref(null)
const fileInput = ref(null)
const title = ref('')
const editingGame = ref(null)
const showEditor = ref(false)
const busyGame = ref('')
const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const error = ref('')
const success = ref('')
const accessible = computed(
	() =>
		settings.value?.access?.can_enter ??
		(settings.value?.can_manage || settings.value?.enabled),
)
let timer
let refreshPending = false

function message(err, fallback) {
	return typeof err?.messages?.[0] === 'string' ? err.messages[0] : fallback
}
function editGame(game) {
	editingGame.value = { ...game }
	showEditor.value = true
}
async function onEdited() {
	success.value = '游戏信息已更新。'
	await refresh()
}
async function downloadGame(game) {
	if (busyGame.value) return
	busyGame.value = game.name
	error.value = ''
	try {
		const result = await call('lms.lms.game.download_game', { name: game.name })
		saveGameDownload(result.filename, result.content)
	} catch (err) {
		error.value = message(err, '下载失败，请重试。')
	} finally {
		busyGame.value = ''
	}
}
async function deleteGame(game) {
	if (
		busyGame.value ||
		!window.confirm(`确定删除“${game.title}”吗？删除后无法恢复。`)
	)
		return
	busyGame.value = game.name
	error.value = ''
	try {
		await call('lms.lms.game.delete_game', { name: game.name })
		games.value = games.value.filter((item) => item.name !== game.name)
		success.value = '游戏已删除。'
	} catch (err) {
		error.value = message(err, '删除失败，请重试。')
	} finally {
		busyGame.value = ''
	}
}
async function refresh() {
	if (loading.value) {
		refreshPending = true
		return
	}
	loading.value = true
	error.value = ''
	try {
		settings.value = await call('lms.lms.game.get_game_settings')
		if (settings.value.can_manage && !courses.value.length) {
			try {
				courses.value =
					(await call('lms.lms.game_access.get_access_options')).courses || []
			} catch {
				/* The access tab provides its own recoverable error state. */
			}
		}
		if (accessible.value) {
			games.value = await call('lms.lms.game.get_games')
		} else {
			games.value = []
		}
		await settingsStore.loadSidebarSettings(true)
	} catch (err) {
		games.value = []
		error.value = message(err, '无法加载游戏，请刷新重试。')
	} finally {
		loading.value = false
		if (refreshPending) {
			refreshPending = false
			refresh()
		}
	}
}
async function toggleGameAvailability(event, game) {
	const enabled = event.target.checked ? 1 : 0
	event.target.checked = !!game.enabled
	if (busyGame.value || loading.value) return
	busyGame.value = game.name
	error.value = ''
	success.value = ''
	try {
		const result = await call('lms.lms.game.set_game_availability', {
			name: game.name,
			enabled,
		})
		const current = games.value.find((item) => item.name === result.name)
		if (current) current.enabled = result.enabled
		success.value = `“${game.title}”已${result.enabled ? '启用' : '关闭'}。`
	} catch (err) {
		error.value = message(err, '保存失败，请重试。')
	} finally {
		busyGame.value = ''
	}
}
async function toggleVisibility(event) {
	const enabled = event.target.checked ? 1 : 0
	event.target.checked = settings.value.enabled
	saving.value = true
	error.value = ''
	try {
		settings.value = await call('lms.lms.game.set_game_enabled', { enabled })
		await settingsStore.loadSidebarSettings(true)
	} catch (err) {
		error.value = message(err, '保存失败，请重试。')
	} finally {
		saving.value = false
	}
}
function selectFile(event) {
	file.value = event.target.files?.[0] || null
	success.value = ''
}
async function upload() {
	if (!file.value || uploading.value) return
	uploading.value = true
	error.value = ''
	success.value = ''
	try {
		const content = await readGameFile(file.value)
		await call('lms.lms.game.upload_game', {
			filename: file.value.name,
			content,
			title: title.value,
		})
		file.value = null
		if (fileInput.value) fileInput.value.value = ''
		title.value = ''
		showUpload.value = false
		activeTab.value = 'library'
		search.value = ''
		format.value = ''
		success.value = '上传成功，点击游戏即可试玩。'
		await refresh()
	} catch (err) {
		error.value = message(err, err?.message || '上传失败，请重试。')
	} finally {
		uploading.value = false
	}
}
watch(
	() => settingsStore.sidebarSettings?.data?.game,
	(visible) => {
		if (visible === 0 && !settings.value?.can_manage) {
			if (settings.value) settings.value.enabled = false
			games.value = []
		}
	},
)
onMounted(() => {
	window.addEventListener('lms-game-access-changed', refresh)
	refresh()
	timer = window.setInterval(() => {
		if (
			!document.hidden &&
			!saving.value &&
			!uploading.value &&
			!busyGame.value &&
			!showEditor.value &&
			!showUpload.value
		)
			refresh()
	}, 30000)
})
onUnmounted(() => {
	window.removeEventListener('lms-game-access-changed', refresh)
	window.clearInterval(timer)
})
</script>

<style scoped>
.game-center {
	--accent: #087f68;
	--line: #e1e8e6;
	--muted: #73808f;
	min-height: 100%;
	background: #f6f8fa;
	color: #182b28;
}
.breadcrumb {
	height: 54px;
	display: flex;
	align-items: center;
	gap: 18px;
	padding: 0 32px;
	border-bottom: 1px solid var(--line);
	font-size: 13px;
	color: #617080;
	background: #ffffff70;
}
.breadcrumb span {
	color: #9aa6ae;
}
.page-content {
	max-width: 1600px;
	margin: auto;
	padding: 28px 32px 40px;
}
.page-heading {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 20px;
	margin-bottom: 28px;
}
.page-heading h1 {
	font-size: 30px;
	font-weight: 700;
	letter-spacing: -1px;
}
.page-heading p {
	margin-top: 10px;
	font-size: 14px;
	color: var(--muted);
}
.heading-actions {
	display: flex;
	gap: 10px;
	flex-shrink: 0;
}
.control,
.icon-control {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 8px;
	min-height: 38px;
	border: 1px solid #dce4e8;
	border-radius: 8px;
	background: white;
	font-size: 13px;
	font-weight: 500;
	padding: 8px 14px;
	transition:
		background 0.15s,
		border-color 0.15s;
}
.control:hover,
.icon-control:hover {
	background: #f0f7f4;
	border-color: #abcfc3;
}
.control:disabled,
.icon-control:disabled {
	opacity: 0.5;
	cursor: not-allowed;
}
.control svg,
.icon-control svg {
	width: 16px;
	height: 16px;
	flex-shrink: 0;
}
.primary {
	background: var(--accent);
	color: white;
	border-color: var(--accent);
}
.primary:hover {
	background: #066550;
	border-color: #066550;
}
.icon-control {
	padding: 8px 10px;
}
.full-width {
	width: 100%;
}
.tabs {
	display: flex;
	gap: 24px;
	border-bottom: 1px solid var(--line);
	margin-bottom: 22px;
}
.tabs button {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 0 12px 15px;
	font-size: 14px;
	font-weight: 600;
	border-bottom: 2px solid transparent;
	color: #6d7986;
}
.tabs button.active {
	color: var(--accent);
	border-color: var(--accent);
}
.count {
	background: #e4efeb;
	color: var(--accent);
	padding: 2px 7px;
	border-radius: 20px;
	font-size: 11px;
}
.active .count {
	background: var(--accent);
	color: white;
}
.workspace {
	display: grid;
	grid-template-columns: minmax(0, 1fr) 280px;
	gap: 24px;
	align-items: start;
}
.student-workspace {
	grid-template-columns: 1fr;
}
.library {
	min-width: 0;
}
.library-tools {
	display: flex;
	gap: 12px;
	margin-bottom: 20px;
}
.search-box {
	display: flex;
	align-items: center;
	gap: 10px;
	border: 1px solid var(--line);
	background: white;
	border-radius: 8px;
	padding: 0 12px;
	min-width: 0;
	flex: 1;
}
.search-box svg {
	width: 17px;
	height: 17px;
	color: var(--muted);
	flex-shrink: 0;
}
.search-box input {
	border: 0;
	background: transparent;
	box-shadow: none;
	outline: none;
	width: 100%;
	min-width: 0;
	padding: 10px 0;
	font-size: 13px;
}
.format-select {
	border: 1px solid var(--line);
	border-radius: 8px;
	background-color: white;
	font-size: 13px;
	min-width: 130px;
	padding: 8px 30px 8px 12px;
}
.view-controls {
	display: flex;
	gap: 6px;
}
.selected {
	color: var(--accent);
	background: #e9f5ef;
	border-color: #87bbab;
}
.game-grid {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 18px;
}
.game-card {
	position: relative;
	display: flex;
	flex-direction: column;
	min-width: 0;
	border: 1px solid var(--line);
	border-radius: 12px;
	background: white;
	transition:
		box-shadow 0.2s,
		border-color 0.2s;
}
.game-card:hover {
	border-color: #b8d7cc;
	box-shadow: 0 6px 20px #182b2809;
}
.game-entry {
	text-align: left;
	width: 100%;
	min-width: 0;
}
.game-cover {
	position: relative;
	height: 165px;
	overflow: hidden;
	border-radius: 11px 11px 0 0;
	background: linear-gradient(135deg, #e0f8ec, #afdccc);
	color: #16896c;
	isolation: isolate;
}
.game-cover-1 {
	background: linear-gradient(135deg, #172752, #395b90);
	color: #a4dcff;
}
.game-cover-2 {
	background: linear-gradient(135deg, #fff0d7, #f6cba5);
	color: #d2813d;
}
.game-cover-3 {
	background: linear-gradient(135deg, #ece8ff, #c8c3f5);
	color: #8073db;
}
.game-cover-4 {
	background: linear-gradient(135deg, #e0f4ff, #acdaef);
	color: #2899b4;
}
.game-cover-5 {
	background: linear-gradient(135deg, #edf3d9, #cbdab0);
	color: #729b4e;
}
.game-cover-image {
	width: 100%;
	height: 100%;
	object-fit: cover;
}
.cover-icon {
	position: absolute;
	left: 50%;
	top: 50%;
	width: 74px;
	height: 74px;
	transform: translate(-50%, -45%) rotate(-10deg);
	stroke-width: 1.35;
	filter: drop-shadow(0 12px 5px #00000012);
}
.cover-orbit {
	position: absolute;
	width: 180px;
	height: 180px;
	border: 1px solid currentColor;
	opacity: 0.15;
	border-radius: 50%;
	left: 50%;
	top: 50%;
	transform: translate(-50%, -50%);
}
.cover-tile {
	position: absolute;
	width: 55px;
	height: 55px;
	border: 1px solid #ffffff90;
	background: #ffffff35;
	border-radius: 12px;
	transform: rotate(-25deg);
}
.tile-one {
	top: 28px;
	right: 22px;
}
.tile-two {
	bottom: 20px;
	left: 24px;
	width: 35px;
	height: 35px;
	transform: rotate(25deg);
}
.game-badge {
	position: absolute;
	top: 12px;
	left: 12px;
	background: #ffffffe8;
	color: #28535e;
	border: 1px solid #ffffff80;
	border-radius: 5px;
	font-size: 11px;
	font-weight: 600;
	padding: 4px 8px;
}
.game-info {
	padding: 15px 15px 10px;
}
.game-info h2 {
	font-size: 16px;
	line-height: 1.5;
	font-weight: 650;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.description {
	font-size: 13px;
	color: #697888;
	margin-top: 6px;
	overflow: hidden;
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
	min-height: 38px;
	line-height: 19px;
}
.filename {
	font-size: 12px;
	color: #83909e;
	margin-top: 8px;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.game-availability {
	padding: 0 15px 14px;
}
.list-view .game-availability {
	min-width: 125px;
	padding: 14px;
}
.card-actions {
	display: flex;
	gap: 7px;
	margin-top: auto;
	padding: 0 14px 14px;
}
.card-actions > .control {
	flex: 1;
	padding: 7px 8px;
	min-height: 34px;
}
.game-menu {
	position: relative;
}
.game-menu summary {
	list-style: none;
	cursor: pointer;
	min-height: 34px;
}
.game-menu summary::-webkit-details-marker {
	display: none;
}
.menu-items {
	position: absolute;
	right: 0;
	top: 40px;
	z-index: 10;
	padding: 5px;
	background: white;
	box-shadow: 0 5px 25px #182b2826;
	border: 1px solid var(--line);
	border-radius: 8px;
	min-width: 110px;
}
.menu-items button {
	display: block;
	text-align: left;
	width: 100%;
	padding: 9px 12px;
	border-radius: 5px;
	font-size: 13px;
}
.menu-items button:hover {
	background: #f3f6f4;
}
.danger {
	color: #c34444;
}
.busy-status {
	padding: 0 15px 10px;
	font-size: 12px;
	color: var(--muted);
}
.library-footer {
	margin-top: 24px;
	color: var(--muted);
	font-size: 13px;
}
.settings-rail {
	display: grid;
	gap: 18px;
}
.side-card {
	border: 1px solid var(--line);
	border-radius: 12px;
	background: white;
	padding: 20px;
}
.side-card h2 {
	display: flex;
	align-items: center;
	gap: 10px;
	font-size: 17px;
	font-weight: 650;
	margin-bottom: 22px;
}
.side-card h2 svg {
	width: 23px;
	height: 23px;
	color: var(--accent);
}
.visibility-label {
	display: flex;
	align-items: center;
	justify-content: space-between;
	position: relative;
	font-size: 14px;
	cursor: pointer;
}
.visibility-label input {
	position: absolute;
	right: 0;
	opacity: 0;
	width: 40px;
	height: 24px;
	cursor: pointer;
}
.switch-track {
	display: block;
	width: 40px;
	height: 24px;
	border-radius: 20px;
	background: #b5bec3;
	pointer-events: none;
	transition: background 0.2s;
}
.switch-track:after {
	content: '';
	display: block;
	width: 18px;
	height: 18px;
	background: white;
	border-radius: 50%;
	margin: 3px;
	box-shadow: 0 1px 3px #0002;
	transition: transform 0.2s;
}
.visibility-label input:checked + .switch-track {
	background: var(--accent);
}
.visibility-label input:checked + .switch-track:after {
	transform: translateX(16px);
}
.visibility-label input:focus-visible + .switch-track {
	outline: 3px solid #77bbaa;
	outline-offset: 3px;
}
.visibility-label input:disabled + .switch-track {
	opacity: 0.5;
}
.access-state {
	display: flex;
	align-items: center;
	gap: 7px;
	margin: 12px 0 8px;
	color: var(--muted);
	font-size: 12px;
}
.access-state.enabled {
	color: var(--accent);
}
.access-state span {
	width: 7px;
	height: 7px;
	border-radius: 50%;
	background: currentColor;
}
.muted {
	font-size: 12px;
	line-height: 1.8;
	color: var(--muted);
}
.rule-summary {
	border-top: 1px solid var(--line);
	margin-top: 20px;
	padding-top: 20px;
}
.rule-heading {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 8px;
	margin-bottom: 14px;
}
.rule-heading h3 {
	font-size: 13px;
	font-weight: 600;
}
.rule-badge {
	font-size: 10px;
	background: #eaf6f0;
	color: var(--accent);
	border: 1px solid #c1e4d8;
	padding: 5px 6px;
	border-radius: 5px;
}
.course-label {
	display: flex;
	gap: 8px;
	align-items: center;
	padding: 10px 0;
	font-size: 13px;
	overflow-wrap: anywhere;
}
.course-label svg {
	width: 17px;
	flex-shrink: 0;
}
.rule-summary .full-width {
	margin-top: 16px;
}
.info-note {
	display: flex;
	gap: 8px;
	background: #eaf6f1;
	color: #287864;
	padding: 12px 10px;
	border-radius: 7px;
	font-size: 11px;
	line-height: 1.6;
	margin-top: 14px;
}
.info-note svg {
	width: 15px;
	height: 15px;
	flex-shrink: 0;
}
.upload-guide h2 {
	margin-bottom: 16px;
}
.upload-guide > p:not(.muted) {
	font-size: 13px;
	margin-bottom: 8px;
}
.text-link {
	display: flex;
	align-items: center;
	gap: 8px;
	font-size: 12px;
	font-weight: 600;
	color: var(--accent);
	margin-top: 16px;
}
.text-link svg {
	width: 14px;
	height: 14px;
}
.classroom-tip {
	display: flex;
	gap: 12px;
	background: #e8f5ef;
	border: 1px solid #d7ebe3;
	border-radius: 12px;
	padding: 18px;
	color: var(--accent);
}
.classroom-tip > svg {
	width: 23px;
	height: 23px;
	flex-shrink: 0;
}
.classroom-tip h3 {
	font-size: 14px;
	font-weight: 600;
}
.classroom-tip p {
	font-size: 12px;
	line-height: 1.8;
	color: #6d8580;
	margin-top: 7px;
}
.feedback {
	padding: 12px 16px;
	border-radius: 8px;
	font-size: 13px;
	margin-bottom: 18px;
}
.error {
	background: #fff0ef;
	color: #a93c32;
}
.success {
	background: #e7f4ed;
	color: #227351;
}
.empty-state {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 16px;
	border: 1px dashed #cbded5;
	border-radius: 12px;
	padding: 60px 20px;
	text-align: center;
	color: var(--muted);
	background: white;
}
.empty-state > svg {
	width: 42px;
	height: 42px;
	color: var(--accent);
}
.empty-state h2 {
	font-weight: 600;
	color: #253e36;
}
.empty-state p {
	font-size: 13px;
}
.access-panel {
	min-width: 0;
}
.upload-form {
	display: grid;
	gap: 18px;
	font-size: 14px;
	line-height: 1.7;
}
.upload-form > label {
	display: grid;
	gap: 8px;
}
.upload-name {
	border: 1px solid #dce4e0;
	border-radius: 8px;
	padding: 10px 12px;
}
.file-drop {
	position: relative;
	display: flex !important;
	align-items: center;
	justify-content: center;
	flex-direction: column;
	min-height: 185px;
	border: 1px dashed #98c6b6;
	border-radius: 12px;
	background: #f3faf6;
	color: #087f68;
	text-align: center;
	padding: 24px;
	overflow: hidden;
}
.file-drop svg {
	width: 30px;
	height: 30px;
}
.file-drop strong {
	max-width: 100%;
	overflow-wrap: anywhere;
}
.file-drop span {
	font-size: 12px;
	color: #71857e;
}
.file-drop input {
	position: absolute;
	inset: 0;
	opacity: 0;
	cursor: pointer;
	width: 100%;
	height: 100%;
}
.file-drop:focus-within {
	outline: 2px solid #087f68;
	outline-offset: 2px;
}
.list-view {
	grid-template-columns: 1fr;
}
.list-view .game-card {
	flex-direction: row;
	align-items: center;
}
.list-view .game-entry {
	display: flex;
	align-items: center;
	flex: 1;
}
.list-view .game-cover {
	width: 155px;
	height: 125px;
	flex-shrink: 0;
	border-radius: 11px 0 0 11px;
}
.list-view .game-info {
	min-width: 0;
	flex: 1;
}
.list-view .description {
	min-height: 0;
}
.list-view .card-actions {
	margin: 0;
	padding: 14px;
}
.list-view .card-actions > .control {
	flex: none;
}
.game-center button:focus-visible,
.game-center summary:focus-visible {
	outline: 2px solid var(--accent);
	outline-offset: 3px;
}
.search-box:focus-within {
	outline: 2px solid var(--accent);
	outline-offset: 1px;
}
.spinning {
	animation: spin 1s linear infinite;
}
@keyframes spin {
	to {
		transform: rotate(360deg);
	}
}
@media (min-width: 1700px) {
	.game-cover {
		height: 190px;
	}
}
@media (max-width: 1250px) {
	.game-grid:not(.list-view) {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
	.workspace {
		grid-template-columns: minmax(0, 1fr) 255px;
		gap: 18px;
	}
	.student-workspace {
		grid-template-columns: 1fr;
	}
	.page-content {
		padding: 24px;
	}
	.side-card {
		padding: 17px;
	}
	.list-view .game-card {
		flex-wrap: wrap;
	}
	.list-view .card-actions {
		margin-left: auto;
	}
	.library-tools {
		flex-wrap: wrap;
	}
	.search-box {
		flex-basis: 50%;
	}
}
@media (max-width: 1000px) {
	.workspace {
		grid-template-columns: 1fr;
	}
	.settings-rail {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
	.classroom-tip {
		grid-column: 1/-1;
	}
	.game-grid:not(.list-view) {
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
}
@media (max-width: 600px) {
	.breadcrumb {
		padding: 0 18px;
		height: 44px;
	}
	.page-content {
		padding: 20px 16px;
	}
	.page-heading {
		align-items: flex-start;
		flex-direction: column;
		gap: 18px;
	}
	.page-heading h1 {
		font-size: 26px;
	}
	.heading-actions {
		width: 100%;
	}
	.heading-actions .primary {
		flex: 1;
	}
	.tabs {
		gap: 12px;
	}
	.tabs button {
		padding-left: 5px;
		padding-right: 5px;
	}
	.game-grid:not(.list-view) {
		grid-template-columns: 1fr;
	}
	.game-cover {
		height: 190px;
	}
	.settings-rail {
		grid-template-columns: 1fr;
	}
	.library-tools {
		gap: 8px;
	}
	.search-box {
		flex-basis: 100%;
	}
	.format-select {
		flex: 1;
	}
	.list-view .game-cover {
		width: 105px;
		height: 120px;
	}
	.list-view .game-info {
		padding: 12px;
	}
	.list-view .card-actions {
		width: 100%;
		padding-top: 0;
	}
	.list-view .card-actions > .control {
		flex: 1;
	}
	.list-view .game-card {
		overflow: visible;
	}
	.upload-form {
		gap: 14px;
	}
}
@media (prefers-reduced-motion: reduce) {
	*,
	*:before,
	*:after {
		transition: none !important;
		animation: none !important;
	}
}
</style>
