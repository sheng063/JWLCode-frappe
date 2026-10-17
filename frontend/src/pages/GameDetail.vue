<template>
	<div class="mx-auto flex w-full max-w-7xl flex-col gap-5 p-5 sm:p-8">
		<header class="flex flex-wrap items-center justify-between gap-3">
			<div class="flex min-w-0 items-center gap-3">
				<Button @click="router.push({ name: 'Game' })">返回游戏列表</Button>
				<h1 class="break-words text-xl font-semibold text-ink-gray-9">
					{{ game?.title || 'Game' }}
				</h1>
			</div>
			<Button v-if="game" @click="restartGame">重新开始</Button>
		</header>
		<GameAccessNotice
			v-if="settings?.access && !settings.access.can_enter"
			:access="settings.access"
		/>
		<p v-if="loading" role="status">正在打开游戏…</p>
		<div
			v-else-if="error"
			role="alert"
			class="space-y-3 rounded-xl border border-outline-gray-2 p-6"
		>
			<p class="text-ink-gray-7">{{ error }}</p>
			<Button @click="loadGame">重新加载</Button>
		</div>
		<iframe
			v-if="game"
			ref="gameFrame"
			:key="runKey"
			:title="game.title"
			:src="game.url || undefined"
			:srcdoc="game.url ? undefined : gameDocument(game.html, game.connect_sources)"
			sandbox="allow-scripts allow-pointer-lock"
			allow="fullscreen; autoplay"
			referrerpolicy="no-referrer"
			class="w-full rounded-xl border border-outline-gray-2 bg-white"
			style="height: calc(100dvh - 160px); min-height: 360px"
		/>
	</div>
</template>

<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Button, call } from 'frappe-ui'
import { useSettings } from '@/stores/settings'
import { gameDocument } from '@/utils/game'
import { createGameBridge } from '@/utils/gameRuntime'
import GameAccessNotice from '@/components/GameAccessNotice.vue'

const props = defineProps({ gameId: { type: String, required: true } })
const router = useRouter()
const settingsStore = useSettings()
const game = ref(null)
const settings = ref(null)
const error = ref('')
const loading = ref(false)
const runKey = ref(0)
const gameFrame = ref(null)
let bridge
let launchId = null

function closeLaunch() {
	bridge?.reset()
	const previous = launchId
	launchId = null
	if (previous) call('lms.lms.game_runtime.close_launch', { launch_id: previous }).catch(() => {})
}
function restartGame() {
	if (launchId) loadGame()
	else runKey.value++
}
let requestVersion = 0
let timer
let checking = false
let recheckPending = false

function revokeAccess() {
	closeLaunch()
	requestVersion++
	game.value = null
	loading.value = false
	error.value = settings.value?.access ? '' : '教师尚未开放 Game 模块。'
}
function revokeGameAccess() {
	closeLaunch()
	requestVersion++
	game.value = null
	loading.value = false
	error.value = '教师已关闭此游戏，请等待重新启用。'
}
async function loadGame() {
	closeLaunch()
	const version = ++requestVersion
	game.value = null
	error.value = ''
	loading.value = true
	try {
		const access = await call('lms.lms.game.get_game_settings', {
			name: props.gameId,
		})
		if (version !== requestVersion) return
		settings.value = access
		if (!(access.access?.can_enter ?? (access.can_manage || access.enabled)))
			return revokeAccess()
		if (access.game_enabled === false) return revokeGameAccess()
		let result = await call('lms.lms.game.get_game', { name: props.gameId })
		if (version !== requestVersion) return
		if (result.runtime_mode === 'UniversalRelay') {
			result = await call('lms.lms.game_runtime.create_launch', { game: props.gameId })
			if (version !== requestVersion) {
				call('lms.lms.game_runtime.close_launch', { launch_id: result.launch_id }).catch(() => {})
				return
			}
			launchId = result.launch_id
		}
		game.value = result
		runKey.value++
	} catch (err) {
		if (version !== requestVersion) return
		error.value = '无法打开游戏，游戏可能已被删除或教师已关闭访问。'
	} finally {
		if (version === requestVersion) {
			loading.value = false
			if (recheckPending && !checking) {
				recheckPending = false
				checkAccess()
			}
		}
	}
}
async function checkAccess() {
	if (checking || loading.value) {
		recheckPending = true
		return
	}
	checking = true
	const version = requestVersion
	try {
		const access = await call('lms.lms.game.get_game_settings', {
			name: props.gameId,
		})
		if (version !== requestVersion) return
		settings.value = access
		if (!(access.access?.can_enter ?? (access.can_manage || access.enabled)))
			revokeAccess()
		else if (access.game_enabled === false) revokeGameAccess()
		else if (!game.value) await loadGame()
	} catch {
		if (version !== requestVersion) return
		requestVersion++
		closeLaunch()
		game.value = null
		error.value = '无法确认游戏访问权限，请重新加载。'
	} finally {
		checking = false
		if (recheckPending) {
			recheckPending = false
			checkAccess()
		}
	}
}
watch(() => props.gameId, loadGame, { immediate: true })
watch(
	() => settingsStore.sidebarSettings?.data?.game,
	(visible) => {
		if (visible === 0 && !settings.value?.can_manage) revokeAccess()
	},
)
onMounted(() => {
	bridge = createGameBridge({ getFrame: () => gameFrame.value, getLaunch: () => game.value?.launch_id ? game.value : null, call })
	window.addEventListener('lms-game-access-changed', checkAccess)
	window.addEventListener('focus', checkAccess)
	timer = window.setInterval(() => {
		if (!document.hidden) checkAccess()
	}, 30000)
})
onUnmounted(() => {
	closeLaunch()
	bridge?.dispose()
	window.removeEventListener('lms-game-access-changed', checkAccess)
	window.removeEventListener('focus', checkAccess)
	requestVersion++
	window.clearInterval(timer)
})
</script>
