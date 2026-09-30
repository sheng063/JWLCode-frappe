<template>
	<Dialog v-model="open" :options="{ title: '编辑游戏', size: 'lg' }">
		<template #body-content>
			<div class="space-y-5">
				<label class="flex flex-col gap-2 text-sm">
					游戏名称
					<input
						v-model="title"
						maxlength="140"
						:disabled="saving"
						class="rounded border border-outline-gray-2 p-2"
					/>
				</label>
				<label class="flex flex-col gap-2 text-sm">
					游戏简介
					<textarea
						v-model="description"
						maxlength="500"
						rows="3"
						:disabled="saving"
						placeholder="介绍游戏玩法或学习目标"
						class="resize-y rounded border border-outline-gray-2 p-2"
					/>
				</label>
				<div class="space-y-3">
					<div class="cover-preview">
						<img
							v-if="preview"
							:src="preview"
							alt="游戏封面预览"
							class="h-full w-full object-cover"
						/>
						<span v-else>GAME · 默认渐变封面</span>
					</div>
					<label class="flex flex-col gap-2 text-sm">
						更换封面
						<input
							type="file"
							accept=".jpg,.jpeg,.png,.webp"
							:disabled="saving || reading"
							@change="selectCover"
						/>
					</label>
					<p class="text-sm text-ink-gray-5">
						支持 JPG、PNG、WebP，最大 2 MB。建议使用横向图片。
					</p>
					<Button
						v-if="preview"
						:disabled="saving || reading"
						@click="removeCover"
						>恢复默认封面</Button
					>
				</div>
				<p v-if="error" role="alert" class="text-sm text-ink-red-4">
					{{ error }}
				</p>
			</div>
		</template>
		<template #actions>
			<Button
				variant="solid"
				:loading="saving"
				:disabled="saving || reading || !title.trim()"
				@click="save"
				>保存修改</Button
			>
			<Button :disabled="saving" @click="open = false">取消</Button>
		</template>
	</Dialog>
</template>
<script setup>
import { ref, watch } from 'vue'
import { Button, Dialog, call } from 'frappe-ui'
import { readGameCover } from '@/utils/game'
const props = defineProps({ game: { type: Object, required: true } })
const emit = defineEmits(['saved'])
const open = defineModel({ type: Boolean, default: false })
const title = ref('')
const description = ref('')
const preview = ref('')
const cover = ref(null)
const error = ref('')
const saving = ref(false)
const reading = ref(false)
let coverRequest = 0
watch(
	() => [open.value, props.game],
	() => {
		coverRequest++
		reading.value = false
		if (!open.value) return
		title.value = props.game.title
		description.value = props.game.description || ''
		preview.value = props.game.cover_image || ''
		cover.value = null
		error.value = ''
	},
	{ immediate: true }
)
async function selectCover(event) {
	const file = event.target.files?.[0]
	if (!file) return
	const request = ++coverRequest
	reading.value = true
	error.value = ''
	try {
		const image = await readGameCover(file)
		if (request !== coverRequest) return
		cover.value = image.content
		preview.value = image.preview
	} catch (err) {
		if (request === coverRequest) error.value = err.message
	} finally {
		if (request === coverRequest) reading.value = false
		event.target.value = ''
	}
}
function removeCover() {
	cover.value = ''
	preview.value = ''
}
async function save() {
	if (saving.value || reading.value || !title.value.trim()) return
	saving.value = true
	error.value = ''
	try {
		await call('lms.lms.game.update_game', {
			name: props.game.name,
			title: title.value.trim(),
			description: description.value,
			cover: cover.value,
		})
		open.value = false
		emit('saved')
	} catch (err) {
		error.value = err.messages?.[0] || '保存失败，请重试。'
	} finally {
		saving.value = false
	}
}
</script>
<style scoped>
.cover-preview {
	height: 180px;
	overflow: hidden;
	border-radius: 12px;
	display: grid;
	place-items: center;
	color: white;
	font-weight: 600;
	background: linear-gradient(125deg, #4338ca, #0e7490);
}
</style>
