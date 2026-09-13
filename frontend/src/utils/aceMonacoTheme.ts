import ace from 'ace-builds'
import cssText from '@/styles/aceMonacoTheme.css?inline'

// Monaco-inspired light colors, using Ace's existing language tokenizers.
ace.define('ace/theme/monaco', ['require', 'exports', 'module'], () => ({
	isDark: false,
	cssClass: 'ace-monaco',
	cssText,
}))
