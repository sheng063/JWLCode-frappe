<template>
 <section class="submission-detail" aria-label="提交详情">
  <p v-if="loading && !doc" role="status">正在加载提交记录…</p>
  <p v-if="error" role="alert">提交记录加载失败。<button @click="refresh">重试</button></p>
  <template v-if="doc">
   <header><strong :class="doc.status === 'Passed' ? 'text-green-500' : pending ? 'text-ink-gray-6' : 'text-red-500'">{{ labels[doc.status] || doc.status }}</strong><span class="ml-3 text-ink-gray-6">{{ counts }}</span></header>
   <p class="my-3 text-sm text-ink-gray-6">{{ doc.member_name || doc.member || doc.owner }} 提交于 <time :datetime="doc.creation">{{ doc.creation }}</time></p>
   <p v-if="pending" role="status">代码正在评测中…</p>
   <div v-else-if="doc.status === 'Passed'" class="metrics">
    <div>执行用时<strong>{{ doc.time_ms == null ? '暂无数据' : `${doc.time_ms} ms` }}</strong></div>
    <div>消耗内存<strong>{{ doc.memory_kb == null ? '暂无数据' : `${(doc.memory_kb / 1024).toFixed(2)} MB` }}</strong></div>
   </div>
   <template v-else><h3>关键报错信息</h3><pre class="error-message">{{ doc.compiler_message || labels[doc.status] || doc.status }}</pre><h3>最后执行的输入</h3><pre>{{ failedCase?.input ?? '暂无可展示的输入' }}</pre></template>
   <div class="flex items-center justify-between gap-3 mt-6 mb-3"><span>代码 · {{ doc.language }}</span><div class="flex gap-3"><button aria-label="复制提交代码" @click="copy">{{ copied ? '已复制' : '复制' }}</button><button @click="emit('restore', doc)">复制到编辑器</button></div></div>
   <p v-if="copyError" role="alert">复制失败，请重试或手动选择代码复制。</p>
   <pre class="source"><code>{{ doc.code }}</code></pre>
  </template>
 </section>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { call } from 'frappe-ui'
const props = defineProps<{ name: string; revision?: string }>()
const emit = defineEmits<{ restore: [doc: any] }>()
const doc = ref<any>(null)
const loading = ref(false)
const error = ref(false)
const copied = ref(false)
const copyError = ref(false)
const labels: Record<string, string> = {
 Passed: '通过', Failed: '错误解答', 'Wrong Answer': '错误解答', 'Runtime Error': '执行出错', 'Compilation Error': '编译出错', 'Time Limit Exceeded': '超出时间限制', 'Memory Limit Exceeded': '超出内存限制', 'Output Limit Exceeded': '超出输出限制', 'Connection Timeout': '连接超时', 'System Error': '系统错误', Queued: '排队中', Compiling: '编译中', Running: '运行中', Canceled: '已取消',
}
const pending = computed(() => ['Queued', 'Compiling', 'Running'].includes(doc.value?.status))
const failedCase = computed(() => doc.value?.test_cases?.find((item: any) => item.status === 'Failed'))
const counts = computed(() => {
 const value = doc.value
 if (value.total_tests > 0) return `${value.passed_tests ?? 0} / ${value.total_tests} 个通过的测试用例`
 if (value.test_cases?.length && !value.judge_request_id) return `${value.test_cases.filter((item: any) => item.status === 'Passed').length} / ${value.test_cases.length} 个通过的测试用例`
 return '测试用例数量暂无数据'
})
let timer: ReturnType<typeof setTimeout> | undefined
let disposed = false
async function refresh() {
 if (loading.value || disposed) return
 clearTimeout(timer)
 loading.value = true
 error.value = false
 try {
  await call('lms.lms.judge_service.get_programming_submission_status', { submission: props.name })
  const result = await call('frappe.client.get', { doctype: 'LMS Programming Exercise Submission', name: props.name })
  if (!disposed) doc.value = result
 } catch { error.value = true }
 finally { loading.value = false; if (!disposed && pending.value && !error.value) timer = setTimeout(refresh, 1500) }
}
async function copy() {
 try { await navigator.clipboard.writeText(doc.value.code || ''); copied.value = true; copyError.value = false }
 catch { copyError.value = true }
}
watch(() => [props.name, props.revision], refresh, { immediate: true })
onBeforeUnmount(() => { disposed = true; clearTimeout(timer) })
</script>
<style scoped>
.submission-detail { flex: 1; min-height: 0; overflow: auto; padding: 24px; background: var(--surface-white); }
h3 { margin-top: 20px; color: var(--ink-gray-6); font-size: 14px; }
pre { padding: 16px; margin-top: 10px; border-radius: 8px; background: var(--surface-gray-1); white-space: pre-wrap; overflow-wrap: anywhere; font-size: 13px; }
.source { white-space: pre; overflow: auto; tab-size: 4; }
.error-message { background: #fff1f2; color: #dc2626; }
.metrics { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin: 24px 0; }
.metrics > div { background: var(--surface-gray-1); padding: 20px; border-radius: 8px; }
.metrics strong { display: block; margin-top: 12px; font-size: 22px; }
</style>
