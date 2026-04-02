# CLAUDE.md

请在启动时加载 AGENT.md 以获取你的身份和通信协议。

@import AGENT.md

## 行为指引

1. 在每次会话或接到新指令时，**先**用 Inbox API（可用 `curl`）检查未读；有任务则优先按邮件需求实现，再处理其它事项。
2. 按照 AGENT.md 中的身份提示词行事。
3. 完成任务后通过 Reply 或 Forward 将结果发送给下一环节；收尾前可再查一次 Inbox。
4. 所有通信必须经过 Mail Broker，使用你的邮箱地址: `askmany-monitor-coder@local`

说明：纯 CLI 会话无法像「系统定时任务」那样每分钟无人值守唤醒；若需要无人值守轮询，需配合外部调度或产品能力，而不是仅靠本文件。
