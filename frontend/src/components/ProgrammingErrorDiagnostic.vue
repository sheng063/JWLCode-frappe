<template>
 <section class="diagnostic" aria-label="错误详情">
  <div class="font-semibold">错误详情</div>
  <pre>{{ message || '评测服务未返回详细错误信息，无法定位具体代码行。' }}</pre>
  <template v-if="locations.length">
   <div class="font-semibold mt-3">错误位置与代码</div>
   <pre v-for="line in locations" :key="line">第 {{ line }} 行：{{ lines[line - 1] }}</pre>
  </template>
 </section>
</template>
<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ message?: string | null; code: string }>()
const lines = computed(() => props.code.split('\n'))
const locations = computed(() => {
 const found = [...(props.message || '').matchAll(/(?:File "[^"\n]+", line (\d+)|[^\s:]+\.(?:cpp|cc|c|py):(\d+)(?::\d+)?)/g)]
 return [...new Set(found.map(match => Number(match[1] || match[2])))].filter(line => line > 0 && line <= lines.value.length)
})
</script>
<style scoped>
.diagnostic { padding: 16px; border-radius: 8px; background: #fff1f2; color: #b91c1c; margin-top: 12px; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; margin-top: 8px; font-size: 13px; }
</style>
