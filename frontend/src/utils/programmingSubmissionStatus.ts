export const submissionStatusLabels: Record<string, string> = {
 Passed: '通过', Failed: '错误解答', 'Wrong Answer': '错误解答', 'Runtime Error': '执行出错', 'Compilation Error': '编译出错', 'Time Limit Exceeded': '超出时间限制', 'Memory Limit Exceeded': '超出内存限制', 'Output Limit Exceeded': '超出输出限制', 'Connection Timeout': '连接超时', 'System Error': '系统错误', Queued: '排队中', Compiling: '编译中', Running: '运行中', Canceled: '已取消',
}

const judgeStatuses: Record<string, string> = {
 ACCEPTED: 'Passed', Accepted: 'Passed', WRONG_ANSWER: 'Failed',
 RUNTIME_ERROR: 'Runtime Error', COMPILE_ERROR: 'Compilation Error',
 TIME_LIMIT_EXCEEDED: 'Time Limit Exceeded', MEMORY_LIMIT_EXCEEDED: 'Memory Limit Exceeded',
 OUTPUT_LIMIT_EXCEEDED: 'Output Limit Exceeded', CONNECTION_TIMEOUT: 'Connection Timeout',
 SYSTEM_ERROR: 'System Error', QUEUED: 'Queued', COMPILING: 'Compiling', RUNNING: 'Running', CANCELED: 'Canceled',
}
export function submissionStatusLabel(status: string) {
 return submissionStatusLabels[judgeStatuses[status] || status] || '未知评测状态'
}
