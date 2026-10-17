import './index.css'
import { createApp, watch } from 'vue'
import router from './router'
import App from './App.vue'
import { createPinia } from 'pinia'
import dayjs from '@/utils/dayjs'
import { createDialog } from '@/utils/dialogs'
import translationPlugin from './translation'
import { usersStore } from './stores/user'
import { useSettings } from './stores/settings'
import { initSocket } from './socket'
import { FrappeUI, setConfig, frappeRequest, pageMetaPlugin } from 'frappe-ui'
import { telemetryPlugin } from 'frappe-ui/frappe'
import { registerDirectives } from './directives'

let pinia = createPinia()
let app = createApp(App)
setConfig('resourceFetcher', frappeRequest)

app.use(FrappeUI)
app.use(pinia)
app.use(router)
app.use(translationPlugin)
app.use(pageMetaPlugin)
registerDirectives(app)
app.provide('$dayjs', dayjs)
const socket = initSocket()
app.provide('$socket', socket)
function refreshGameAccess() {
	window.dispatchEvent(new Event('lms-game-access-changed'))
	useSettings()
		.loadSidebarSettings(true)
		.catch(() => {})
}
socket.on('lms_game_visibility_changed', refreshGameAccess)
socket.on('lms_game_access_changed', refreshGameAccess)
app.mount('#app')

const { userResource, allUsers } = usersStore()
app.provide('$user', userResource)
app.provide('$allUsers', allUsers)

watch(userResource, () => {
	if (userResource.data) {
		app.use(telemetryPlugin, { app_name: 'lms' })
	}
})

app.config.globalProperties.$user = userResource
app.config.globalProperties.$dialog = createDialog
