<template>
 <div class="case-editor">
  <div class="case-tabs" aria-label="测试用例">
   <button v-for="(item, index) in cases" :key="index" class="case-tab" :class="{ active: selectedIndex === index }" :aria-pressed="selectedIndex === index" @click="selectedIndex = index">
    <span v-if="passed(index)" class="lucide-square-check text-green-600" aria-label="已通过" />
    {{ index < officialCases.length ? `用例 ${index + 1}` : `自定义 ${index - officialCases.length + 1}` }}
   </button>
   <button class="case-tab" aria-label="添加临时测试用例" :disabled="disabled || cases.length >= 100" @click="add">＋ 添加用例</button>
  </div>
  <template v-if="selectedCase">
   <div v-if="isTemporary" class="temporary-heading"><span>临时用例，刷新页面后清空</span><button aria-label="删除当前临时用例" :disabled="disabled" @click="remove">删除用例</button></div>
   <div class="case-fields">
    <template v-if="isTemporary">
     <label>输入<textarea v-model="selectedCase.input" aria-label="临时用例输入" :disabled="disabled" rows="3" /></label>
     <label>标准输出<textarea v-model="selectedCase.expected_output" aria-label="临时用例标准输出" :disabled="disabled" rows="3" /></label>
    </template>
    <template v-else>
     <div><div>输入</div><pre>{{ selectedCase.input || '—' }}</pre></div>
     <div><div>样例输出</div><pre>{{ selectedCase.expected_output }}</pre></div>
    </template>
   </div>
  </template>
  <p v-else>暂无测试用例，可添加临时用例。</p>
 </div>
</template>
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
export type TemporaryTestCase = { input: string; expected_output: string }
const props = withDefaults(defineProps<{ officialCases?: TemporaryTestCase[]; results?: any[]; disabled?: boolean }>(), { officialCases: () => [], results: () => [], disabled: false })
// 临时用例只存在父页面内存中，不修改题目样例或浏览器存储。
const temporaryCases = defineModel<TemporaryTestCase[]>({ required: true })
const selectedIndex = ref(temporaryCases.value.length ? props.officialCases.length + temporaryCases.value.length - 1 : 0)
const cases = computed(() => [...props.officialCases, ...temporaryCases.value])
const selectedCase = computed(() => cases.value[selectedIndex.value])
const isTemporary = computed(() => selectedIndex.value >= props.officialCases.length)
watch(() => temporaryCases.value.length, (length, previous) => {
 selectedIndex.value = length > previous ? cases.value.length - 1 : Math.min(selectedIndex.value, Math.max(0, cases.value.length - 1))
})
function add() {
 if (props.disabled || cases.value.length >= 100) return
 temporaryCases.value = [...temporaryCases.value, { input: '', expected_output: '' }]
}
function remove() {
 if (props.disabled || !isTemporary.value) return
 temporaryCases.value = temporaryCases.value.filter((_, i) => i !== selectedIndex.value - props.officialCases.length)
}
function passed(index: number) {
 const result = props.results[index]
 const item = cases.value[index]
 return result?.status === 'Passed' && !result.hidden && result.input === item.input && result.expected_output === item.expected_output
}
</script>
<style scoped>
.case-tabs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 18px; }
.case-tab { display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; border-radius: 8px; font-size: 13px; background: var(--surface-gray-1, #f3f3f5); }
.case-tab.active { background: var(--surface-gray-3, #e8e8eb); font-weight: 600; }
button:disabled { opacity: .5; cursor: not-allowed; }
.case-fields { display: grid; gap: 16px; font-size: 13px; }
pre, textarea { display: block; width: 100%; min-height: 48px; margin-top: 8px; border: 0; border-radius: 9px; background: var(--surface-gray-1, #f3f3f5); padding: 13px 16px; font-family: monospace; white-space: pre-wrap; overflow-wrap: anywhere; }
textarea { resize: vertical; }
.temporary-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; font-size: 12px; color: var(--ink-gray-6, #666); }
.temporary-heading button { color: #dc2626; }
</style>
