<template>
	<div class="mx-auto w-full max-w-7xl space-y-6 p-5 sm:p-8">
		<header class="flex flex-wrap items-center justify-between gap-3">
			<div>
				<h1 class="text-2xl font-semibold text-ink-gray-9">Game</h1>
				<p class="mt-2 text-sm text-ink-gray-6">选择游戏，在页面中开始体验。</p>
			</div>
			<Button :loading="loading" @click="refresh">刷新</Button>
		</header>
		<p
			v-if="error"
			role="alert"
			class="rounded-lg bg-surface-red-1 p-3 text-ink-red-4"
		>
			{{ error }}
		</p>
		<p v-if="loading && !settings" role="status">正在加载游戏…</p>
		<template v-if="settings">
			<section
				v-if="settings.can_manage"
				class="space-y-5 rounded-xl border border-outline-gray-2 p-5"
			>
				<label class="flex items-center gap-3">
					<input
						type="checkbox"
						:checked="settings.enabled"
						:disabled="saving"
						@change="toggleVisibility"
					/>
					<span class="text-sm font-medium">向学生显示 Game 模块</span>
					<span v-if="saving" class="text-sm text-ink-gray-5">正在保存…</span>
				</label>
				<p class="text-sm text-ink-gray-6">
					此开关对全站学生生效；关闭后，教师仍可上传和试玩。
				</p>
				<form class="flex flex-wrap items-end gap-4" @submit.prevent="upload">
					<label class="flex flex-col gap-2 text-sm">
						游戏名称（选填）
						<input
							v-model="title"
							:disabled="uploading"
							maxlength="140"
							placeholder="默认使用文件名"
							class="rounded border border-outline-gray-2 p-2"
						/>
					</label>
					<label class="flex min-w-0 flex-col gap-2 text-sm">
						HTML / ZIP 游戏文件
						<input
							ref="fileInput"
							type="file"
							accept=".html,.htm,.zip,text/html,application/zip"
							:disabled="uploading"
							@change="selectFile"
						/>
					</label>
					<Button
						variant="solid"
						type="submit"
						:loading="uploading"
						:disabled="!file || uploading"
						>上传游戏</Button
					>
				</form>
				<p class="text-sm text-ink-gray-5">
					支持 HTML（最大 5 MB）或 ZIP 游戏包（最大 20 MB）。ZIP 中请包含
					index.html 和相关素材，解压后总大小不超过 100 MB。
				</p>
				<p v-if="success" role="status" class="text-sm text-ink-gray-7">
					{{ success }}
				</p>
			</section>
			<p
				v-if="!accessible"
				class="rounded-xl border border-outline-gray-2 p-8 text-center text-ink-gray-6"
			>
				教师尚未开放 Game 模块。
			</p>
			<template v-else>
				<div
					v-if="games.length"
					class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
				>
					<article
						v-for="(game, index) in games"
						:key="game.name"
						class="game-card"
					>
						<button
							class="game-entry"
							@click="
								router.push({
									name: 'GameDetail',
									params: { gameId: game.name },
								})
							"
						>
							<div class="game-cover" :class="`game-cover-${index % 4}`">
								<img
									v-if="game.cover_image"
									:src="game.cover_image"
									alt=""
									loading="lazy"
									class="game-cover-image"
								/>
								<template v-else
									><span class="cover-orbit" /><Gamepad2 class="cover-icon"
								/></template>
								<span class="game-badge">{{
									game.entry_file ? 'ZIP GAME' : 'HTML GAME'
								}}</span>
								<span class="game-play"><Play class="h-4 w-4" />开始游戏</span>
							</div>
							<div class="p-5">
								<h2 class="break-words text-lg font-semibold text-ink-gray-9">
									{{ game.title }}
								</h2>
								<p class="mt-2 line-clamp-2 text-sm leading-5 text-ink-gray-6">
									{{ game.description || '点击进入游戏，开始你的探索。' }}
								</p>
								<p class="mt-3 truncate text-xs text-ink-gray-5">
									{{ game.filename }}
								</p>
							</div>
						</button>
						<div
							v-if="settings.can_manage"
							class="mt-auto flex flex-wrap gap-2 border-t border-outline-gray-2 px-5 py-3"
						>
							<Button :disabled="!!busyGame" @click="editGame(game)"
								>编辑</Button
							>
							<Button :disabled="!!busyGame" @click="downloadGame(game)"
								>下载</Button
							>
							<Button
								theme="red"
								:disabled="!!busyGame"
								@click="deleteGame(game)"
								>删除</Button
							>
							<span
								v-if="busyGame === game.name"
								role="status"
								class="self-center text-xs text-ink-gray-5"
								>处理中…</span
							>
						</div>
					</article>
				</div>
				<p
					v-else-if="!loading"
					class="rounded-xl border border-dashed border-outline-gray-2 p-12 text-center text-ink-gray-6"
				>
					{{
						settings.can_manage
							? '还没有游戏，上传 HTML 文件即可开始。'
							: '还没有游戏，请等待教师上传。'
					}}
				</p>
			</template>
		</template>
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
import { Button, call } from 'frappe-ui'
import { useRouter } from 'vue-router'
import GameEditor from '@/components/GameEditor.vue'
import { Gamepad2, Play } from 'lucide-vue-next'
import { useSettings } from '@/stores/settings'
import { readGameFile, saveGameDownload } from '@/utils/game'

const router = useRouter()
const settingsStore = useSettings()
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
	() => settings.value?.can_manage || settings.value?.enabled
)
let timer

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
	if (loading.value) return
	loading.value = true
	error.value = ''
	try {
		settings.value = await call('lms.lms.game.get_game_settings')
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
		fileInput.value.value = ''
		title.value = ''
		success.value = '上传成功，点击下方游戏即可运行。'
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
	}
)
onMounted(() => {
	refresh()
	timer = window.setInterval(() => {
		if (
			!document.hidden &&
			!saving.value &&
			!uploading.value &&
			!busyGame.value &&
			!showEditor.value
		)
			refresh()
	}, 30000)
})
onUnmounted(() => {
	window.clearInterval(timer)
})
</script>

<style scoped>
.game-card {
	display: flex;
	flex-direction: column;
	overflow: hidden;
	border: 1px solid var(--outline-gray-2, #e5e7eb);
	border-radius: 18px;
	background: var(--surface-cards, #fff);
	transition:
		box-shadow 0.2s,
		transform 0.2s;
}
.game-card:hover {
	transform: translateY(-3px);
	box-shadow: 0 12px 28px rgb(15 23 42 / 10%);
}
.game-entry {
	display: block;
	width: 100%;
	text-align: left;
}
.game-entry:focus-visible {
	outline: 3px solid #6366f1;
	outline-offset: -3px;
	border-radius: 18px;
}
.game-cover {
	position: relative;
	height: 190px;
	overflow: hidden;
	background: linear-gradient(125deg, #4338ca, #0e7490);
	color: white;
}
.game-cover-1 {
	background: linear-gradient(125deg, #9d174d, #c2410c);
}
.game-cover-2 {
	background: linear-gradient(125deg, #065f46, #0e7490);
}
.game-cover-3 {
	background: linear-gradient(125deg, #6b21a8, #be185d);
}
.game-cover-image {
	width: 100%;
	height: 100%;
	object-fit: cover;
	transition: transform 0.3s;
}
.game-entry:hover .game-cover-image {
	transform: scale(1.04);
}
.cover-orbit {
	position: absolute;
	width: 240px;
	height: 240px;
	border: 35px solid rgb(255 255 255 / 8%);
	border-radius: 50%;
	right: -25px;
	top: -65px;
}
.cover-icon {
	position: absolute;
	width: 85px;
	height: 85px;
	right: 25px;
	bottom: 35px;
	opacity: 0.75;
	transform: rotate(-12deg);
	stroke-width: 1.3;
}
.game-badge {
	position: absolute;
	left: 18px;
	top: 18px;
	font-size: 10px;
	letter-spacing: 0.12em;
	background: rgb(0 0 0 / 35%);
	padding: 6px 9px;
	border-radius: 6px;
}
.game-play {
	position: absolute;
	left: 18px;
	bottom: 18px;
	display: flex;
	align-items: center;
	gap: 7px;
	font-size: 13px;
	font-weight: 600;
	background: rgb(0 0 0 / 55%);
	padding: 9px 13px;
	border-radius: 999px;
}
@media (prefers-reduced-motion: reduce) {
	.game-card,
	.game-cover-image {
		transition: none;
	}
}
</style>
