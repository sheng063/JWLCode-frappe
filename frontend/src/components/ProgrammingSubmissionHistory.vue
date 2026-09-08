<template>
	<section class="submission-history" aria-label="提交记录">
		<div class="history-filters">
			<select v-model="status" aria-label="筛选提交状态">
				<option value="">所有状态</option>
				<option v-for="(label, value) in statuses" :key="value" :value="value">{{ label }}</option>
			</select>
			<select v-model="language" aria-label="筛选提交语言">
				<option value="">所有语言</option>
				<option>Python</option>
				<option>C++</option>
			</select>
			<button aria-label="刷新提交记录" @click="history.reload()"><span class="lucide-refresh-cw size-4" /></button>
		</div>
		<p v-if="history.error" role="alert" class="p-4 text-red-500">提交记录加载失败，请点击刷新重试。</p>
		<p v-else-if="history.loading" role="status" class="p-4 text-ink-gray-6">正在加载提交记录…</p>
		<template v-else>
			<table v-if="history.data?.length" class="history-table">
				<thead><tr><th scope="col">#</th><th scope="col">状态 / 时间</th><th scope="col">语言</th><th scope="col">执行用时</th><th scope="col">消耗内存</th></tr></thead>
				<tbody>
					<tr v-for="(row, index) in history.data" :key="row.name" tabindex="0" class="cursor-pointer" @click="emit('select', row.name)" @keydown.enter.prevent="emit('select', row.name)" @keydown.space.prevent="emit('select', row.name)">
						<td class="text-ink-gray-5">{{ index + 1 }}</td>
						<td><span :class="row.status === 'Passed' ? 'text-green-500' : pending.includes(row.status) ? 'text-ink-gray-6' : 'text-red-500'" class="font-semibold">{{ statuses[row.status] || row.status }}</span><time :datetime="row.creation" :title="row.creation" class="block mt-1 text-ink-gray-6">{{ dayjs ? dayjs(row.creation).fromNow() : row.creation }}</time></td>
						<td><span class="history-language">{{ row.language }}</span></td>
						<td class="whitespace-nowrap">{{ metric(row, 'time_ms') }}</td>
						<td class="whitespace-nowrap">{{ metric(row, 'memory_kb') }}</td>
					</tr>
				</tbody>
			</table>
			<p v-else class="p-6 text-center text-ink-gray-6">暂无提交记录</p>
		</template>
		<button v-if="history.hasNextPage" :disabled="history.loading" class="p-4 w-full text-ink-gray-6" @click="history.next()">加载更多</button>
	</section>
</template>

<script setup lang="ts">
import { inject, ref, watch } from 'vue'
import { createListResource } from 'frappe-ui'

const props = defineProps<{ exercise: string; member?: string; revision?: string }>()
const emit = defineEmits<{ select: [name: string] }>()
const dayjs = inject<any>('$dayjs', null)
const status = ref('')
const language = ref('')
const pending = ['Queued', 'Compiling', 'Running']
const statuses: Record<string, string> = {
	'Output Limit Exceeded': '超出输出限制', 'Connection Timeout': '连接超时',
	Passed: '通过', Failed: '错误解答', 'Runtime Error': '执行出错',
	'Compilation Error': '编译错误', 'Time Limit Exceeded': '超出时间限制',
	'Memory Limit Exceeded': '超出内存限制', 'System Error': '系统错误',
	Queued: '排队中', Compiling: '编译中', Running: '运行中', Canceled: '已取消',
}
const history = createListResource({
	doctype: 'LMS Programming Exercise Submission',
	fields: ['name', 'creation', 'status', 'language', 'time_ms', 'memory_kb'],
	orderBy: 'creation desc', pageLength: 20, auto: false,
})
watch(() => [props.exercise, props.member, props.revision, status.value, language.value], () => {
	if (!props.member) { history.data = []; return }
	history.update({ filters: {
		exercise: props.exercise, member: props.member,
		...(status.value ? { status: status.value } : {}),
		...(language.value ? { language: language.value } : {}),
	} })
	history.reload()
}, { immediate: true })

function metric(row: any, field: 'time_ms' | 'memory_kb') {
	const value = row[field]
	if (pending.includes(row.status) || value == null ||
		(value === 0 && row.status !== 'Passed' && row.status !== 'Failed')) return 'N/A'
	return field === 'time_ms' ? `${value} ms` : `${(value / 1024).toFixed(1)} MB`
}
</script>

<style scoped>
.submission-history { flex: 1; min-height: 0; overflow: auto; }
.history-filters { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-bottom: 1px solid var(--outline-gray-2); }
.history-filters select { min-width: 0; flex: 1; border: 0; background-color: transparent; color: var(--ink-gray-6); font-size: 14px; }
.history-table { width: 100%; font-size: 13px; text-align: left; }
.history-table th { padding: 12px 10px; font-weight: 400; color: var(--ink-gray-6); white-space: nowrap; }
.history-table td { padding: 16px 10px; }
.history-table tbody tr:nth-child(even) { background: var(--surface-gray-1); }
.history-language { padding: 3px 8px; border-radius: 999px; background: var(--surface-gray-2); }
</style>
