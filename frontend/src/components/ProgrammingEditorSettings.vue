<template>
	<Dialog v-model:open="open" title="设置" size="3xl">
		<template #default>
			<div class="editor-settings-layout">
				<nav class="editor-settings-nav" aria-label="设置菜单">
					<button
						v-for="item in menus"
						:key="item.value"
						type="button"
						:class="{ selected: menu === item.value }"
						:aria-pressed="menu === item.value"
						@click="menu = item.value"
					>
						<span :class="item.icon" />{{ item.label }}
					</button>
				</nav>
				<div class="editor-settings-body">
					<template v-if="menu === 'editor'">
						<label class="setting-row">主题<select v-model="preferences.theme" aria-label="主题">
							<option value="light">明亮模式</option>
							<option value="dark">暗黑模式</option>
							<option value="monaco">Monaco 高亮（浅色）</option>
						</select></label>
						<label class="setting-row"
							>字体<select v-model="preferences.fontFamily" aria-label="字体">
								<option value="monospace">Default</option>
								<option value="Menlo, monospace">Menlo</option>
								<option value="Consolas, monospace">Consolas</option>
								<option value="Monaco, monospace">Monaco</option>
								<option value="JetBrains Mono, monospace">JetBrains Mono</option>
							</select></label
						>
						<label class="setting-row"
							>字体大小<select v-model.number="preferences.fontSize" aria-label="字体大小">
								<option
									v-for="size in [12, 13, 14, 16, 18, 20, 24]"
									:key="size"
									:value="size"
								>
									{{ size }}px
								</option>
							</select></label
						>
						<label class="setting-row"
							>字体连字<input
								v-model="preferences.fontLigatures"
								type="checkbox"
								role="switch"
						/></label>
						<label class="setting-row"
							>键位绑定<select v-model="preferences.keyboard">
								<option value="standard">Standard</option>
								<option value="vim">Vim</option>
								<option value="emacs">Emacs</option>
							</select></label
						>
						<label class="setting-row"
							>Tab 长度<select v-model.number="preferences.tabSize">
								<option v-for="size in [2, 4, 8]" :key="size" :value="size">
									{{ size }} 个空格
								</option>
							</select></label
						>
						<label class="setting-row"
							>自动换行<input
								v-model="preferences.wrap"
								type="checkbox"
								role="switch"
						/></label>
						<label class="setting-row"
							>显示相对行号<input
								v-model="preferences.relativeLineNumbers"
								type="checkbox"
								role="switch"
						/></label>
						<label class="setting-row"
							>基础代码补全<input
								v-model="preferences.autocomplete"
								type="checkbox"
								role="switch"
						/></label>
					</template>
					<template v-else>
						<p class="text-sm text-ink-gray-5 mb-3">常规</p>
						<label class="setting-row"
							>执行代码<span class="shortcut"
								><input
									v-model="preferences.runShortcut"
									type="checkbox"
									role="switch"
								/><kbd>{{ modifier }}</kbd
								><kbd>Enter</kbd></span
							></label
						>
						<label class="setting-row"
							>提交解答<span class="shortcut"
								><input
									v-model="preferences.submitShortcut"
									type="checkbox"
									role="switch"
								/><kbd>{{ modifier }}</kbd
								><kbd>⇧</kbd><kbd>Enter</kbd></span
							></label
						>
						<div class="setting-row">
							代码格式化<span class="shortcut"
								><kbd>Alt</kbd><kbd>⇧</kbd><kbd>F</kbd></span
							>
						</div>
						<div class="setting-row">
							展开 / 还原代码面板<span class="shortcut"
								><kbd>Alt</kbd><kbd>F</kbd></span
							>
						</div>
						<div
							class="border-t border-outline-gray-2 mt-4 pt-4 text-sm text-ink-gray-5"
						>
							代码编辑器（Standard）
						</div>
						<div
							v-for="shortcut in shortcuts"
							:key="shortcut.label"
							class="setting-row"
						>
							{{ shortcut.label
							}}<span class="shortcut"
								><kbd v-for="key in shortcut.keys" :key="key">{{
									key
								}}</kbd></span
							>
						</div>
					</template>
				</div>
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { Dialog } from 'frappe-ui'
import type { EditorPreferences } from '@/utils/editorPreferences'
const open = defineModel<boolean>('open', { default: false })
const preferences = defineModel<EditorPreferences>({ required: true })
const menu = ref('editor')
const modifier = /Mac|iPhone|iPad/.test(navigator.platform) ? '⌘' : 'Ctrl'
const menus = [
	{ value: 'editor', label: '代码编辑器', icon: 'lucide-code-xml size-4' },
	{ value: 'shortcuts', label: '键盘快捷键', icon: 'lucide-keyboard size-4' },
]
const shortcuts = [
	{ label: '行缩进', keys: ['Tab'] },
	{ label: '行减少缩进', keys: ['⇧', 'Tab'] },
	{ label: '切换行注释', keys: [modifier, '/'] },
	{ label: '查找', keys: [modifier, 'F'] },
	{ label: '撤销', keys: [modifier, 'Z'] },
	{ label: '重做', keys: modifier === '⌘' ? ['⌘', '⇧', 'Z'] : ['Ctrl', 'Y'] },
]
</script>
<style scoped>
.editor-settings-layout {
	display: flex;
	min-height: 370px;
	margin: -8px;
}
.editor-settings-nav {
	width: 160px;
	flex-shrink: 0;
	padding: 16px 10px;
	background: var(--surface-gray-2, #f5f5f5);
}
.editor-settings-nav button {
	display: flex;
	align-items: center;
	gap: 8px;
	width: 100%;
	padding: 12px 10px;
	border-radius: 8px;
	font-size: 14px;
	text-align: left;
}
.editor-settings-nav button.selected {
	background: var(--surface-gray-3, #eaeaea);
	font-weight: 600;
}
.editor-settings-body {
	flex: 1;
	min-width: 0;
	padding: 12px 24px;
	max-height: 65vh;
	overflow-y: auto;
}
.setting-row {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16px;
	min-height: 42px;
	font-size: 14px;
}
.setting-row select {
	max-width: 150px;
	border: 0;
	border-radius: 5px;
	background-color: var(--surface-gray-2, #f5f5f5);
	padding: 4px 28px 4px 8px;
	font-size: 12px;
}
.setting-row input[type='checkbox'] {
	appearance: none;
	width: 30px;
	height: 18px;
	border: 0;
	border-radius: 10px;
	background: #bfc1c4;
	cursor: pointer;
	position: relative;
	flex-shrink: 0;
}
.setting-row input[type='checkbox']::after {
	content: '';
	position: absolute;
	width: 14px;
	height: 14px;
	border-radius: 50%;
	background: white;
	top: 2px;
	left: 2px;
	transition: transform 0.15s;
}
.setting-row input:checked {
	background: #1677ff;
}
.setting-row input:checked::after {
	transform: translateX(12px);
}
.shortcut {
	display: flex;
	align-items: center;
	gap: 5px;
}
kbd {
	border: 1px solid var(--outline-gray-2, #ddd);
	border-radius: 3px;
	padding: 2px 5px;
	font-size: 12px;
}
@media (max-width: 540px) {
	.editor-settings-layout {
		flex-direction: column;
	}
	.editor-settings-nav {
		width: 100%;
		display: flex;
		padding: 6px;
	}
	.editor-settings-body {
		padding: 12px;
	}
}
</style>
