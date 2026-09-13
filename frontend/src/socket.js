import { io } from 'socket.io-client'
import { socketUrl } from '@/utils/socketUrl'
import { socketio_port } from '../../../../sites/common_site_config.json'

export function initSocket() {
	let host = window.location.hostname
	let siteName = window.site_name || host
	let url = socketUrl(window.location, socketio_port, siteName)

	let socket = io(url, {
		withCredentials: true,
		reconnectionAttempts: 5,
	})
	return socket
}
