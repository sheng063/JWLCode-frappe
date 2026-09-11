<template>
	<SkeletonLoader v-if="loading" variant="header" />
	<header v-else class="header-frame sticky top-0 z-10 justify-between">
		<div class="flex min-w-0 flex-1 items-center gap-2">
			<nav v-if="fullBreadcrumbs" :aria-label="__('Breadcrumbs')" class="flex min-w-0 flex-wrap items-center gap-1 py-2">
				<template v-for="(item, index) in breadcrumbs" :key="index">
					<span v-if="index" class="text-ink-gray-4" aria-hidden="true">/</span>
					<router-link v-if="item.route" :to="item.route" class="break-words text-ink-gray-7 hover:underline">{{ item.label }}</router-link>
					<span v-else class="break-words text-ink-gray-9" :aria-current="index === breadcrumbs.length - 1 ? 'page' : undefined">{{ item.label }}</span>
				</template>
			</nav>
			<template v-else-if="isMobile">
				<router-link
					v-if="backTo"
					:to="backTo"
					:aria-label="__('Back')"
					class="-ms-3 shrink-0 rounded p-1.5 text-ink-gray-9 transition-colors hover:bg-surface-gray-2"
				>
					<span class="lucide-chevron-left size-4 block" />
				</router-link>
				<span class="min-w-0 truncate text-lg-medium text-ink-gray-9">
					{{ currentLabel }}
				</span>
			</template>
			<template v-else>
				<Breadcrumbs class="h-7 min-w-0" :items="breadcrumbs" />
				<Badge v-if="published" theme="green">{{ __('Published') }}</Badge>
			</template>
		</div>
		<div class="flex shrink-0 items-center gap-2">
			<slot name="actions" />
		</div>
	</header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import { Badge, Breadcrumbs } from 'frappe-ui'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import { useScreenSize } from '@/utils/composables'
import type { Breadcrumb } from '@/types'

const props = withDefaults(
	defineProps<{
		breadcrumbs: Breadcrumb[]
		published?: boolean
		loading?: boolean
		fullBreadcrumbs?: boolean
	}>(),
	{ published: false, loading: false }
)

const { isMobile } = useScreenSize()

const currentLabel = computed<string>(
	() => props.breadcrumbs[props.breadcrumbs.length - 1]?.label ?? ''
)

const backTo = computed<RouteLocationRaw | null>(
	() => props.breadcrumbs[props.breadcrumbs.length - 2]?.route ?? null
)
</script>
