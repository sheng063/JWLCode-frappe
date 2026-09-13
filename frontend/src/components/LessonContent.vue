<template>
	<div v-if="youtubeEmbedId(youtube)" :key="youtubeEmbedId(youtube)">
		<div
			class="video-player"
			data-plyr-provider="youtube"
			:data-plyr-embed-id="youtubeEmbedId(youtube)"
		></div>
	</div>
	<!-- Include content in the key so media viewers remount when lessons change. -->
	<div
		v-for="(block, index) in blocks"
		:key="`${index}:${block.text || block.html}`"
	>
		<div v-if="block.type === 'YouTubeVideo'">
			<div
				v-if="youtubeEmbedId(getId(block.text))"
				:key="youtubeEmbedId(getId(block.text))"
				class="video-player"
				data-plyr-provider="youtube"
				:data-plyr-embed-id="youtubeEmbedId(getId(block.text))"
			></div>
		</div>
		<div v-else-if="block.type === 'Quiz'">
			<Quiz :quiz="getId(block.text)" />
		</div>
		<div v-else-if="block.type === 'Video'">
			<video
				controls
				width="100%"
				controlsList="nodownload"
				oncontextmenu="return false;"
			>
				<source :src="safeUrl(getId(block.text))" type="video/mp4" />
			</video>
		</div>
		<div v-else-if="block.type === 'PDF'">
			<PdfBlock v-if="inlinePdf" :file="getId(block.text)" />
			<iframe
				v-else
				:src="safeUrl(getId(block.text))"
				:title="__('PDF document')"
				width="100%"
				height="700px"
				class="mb-4"
				type="application/pdf"
			></iframe>
		</div>
		<div v-else-if="block.type === 'Audio'">
			<audio width="100%" controls controlsList="nodownload">
				<source :src="safeUrl(getId(block.text))" type="audio/mp3" />
			</audio>
		</div>
		<div v-else-if="block.type === 'Embed'">
			<iframe
				width="100%"
				height="400"
				:src="safeUrl(getId(block.text))"
				:title="__('Embedded content')"
				frameborder="0"
				allowfullscreen
			>
			</iframe>
		</div>
		<div v-else class="lesson-markdown" v-safe-html:rich="block.html"></div>
	</div>
	<div v-if="quizId">
		<Quiz :quiz="quizId" />
	</div>
</template>
<script setup>
import Quiz from '@/components/QuizBlock.vue'
import PdfBlock from '@/components/PdfBlock.vue'
import { computed } from 'vue'
import { lessonContentBlocks } from '@/utils/lessonMarkdown'
import { extractYoutubeID, getMacroArg } from '@/utils/lessonMacros'
import { usesWebkitPdfViewer } from '@/utils/pdfViewer'
import { safeUrl } from '@/utils/safeUrl'

const inlinePdf = usesWebkitPdfViewer()

const props = defineProps({
	content: {
		type: String,
		required: true,
	},
	youtube: {
		type: String,
		required: false,
	},
	quizId: {
		type: String,
		required: false,
	},
})

const blocks = computed(() => lessonContentBlocks(props.content))

const getId = (block) => {
	// Guard the match: a malformed `{{ PDF() }}` / unbalanced-quote macro yields
	// null, and the old unguarded [1] threw and killed the whole lesson render.
	return getMacroArg(block) ?? ''
}

// Both authoring paths (the `youtube` field and the `{{ YouTubeVideo }}` macro)
// must land in the same Plyr-wrapped `.video-player` the EditorJS embed block
// renders. A bare <iframe> is invisible to the watch tracker in Lesson.vue, so
// enforce_video_completion saw "no video" and auto-completed on the dwell timer.
// Falsy id => render nothing rather than a Plyr player with no video, which
// would suppress the dwell timer and leave the lesson uncompletable.
const youtubeEmbedId = (source) => (source ? extractYoutubeID(source) : '')
</script>
