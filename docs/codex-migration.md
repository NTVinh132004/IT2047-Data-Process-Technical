# Chuyển cấu hình Claude sang Codex

Ngày: 30/10/2026. Nguồn thực tế là `~/.claude/`; repo chỉ có `CLAUDE.md`, không có `.claude/` cục bộ. Không sửa nguồn Claude.

## Đã chuyển

- `CLAUDE.md` → `AGENTS.md`, thay cú pháp import `@...` bằng chỉ dẫn đọc file rõ ràng.
- Sáu plugin dạng workflow, cộng bốn skill tài liệu; tổng cộng 60 skill. Bản generation `~g2` được ưu tiên khi trùng tên plugin.
- Skill được cài global trong `~/.codex/skills/`, tài nguyên ở `~/.codex/skill-resources/claude-migration/`; các skill dùng symlink tương đối để giữ đúng liên kết tới script, template và tài liệu đi kèm.
- Giữ license, manifest nguồn và mã helper. Không sao chép credential, lịch sử hội thoại, dữ liệu thật, trash hoặc danh mục marketplace.
- `~/.codex/skill-resources/claude-migration/migration.json` ghi đường dẫn nguồn, phiên bản và SHA-256 của từng SKILL.md nguồn. Các entrypoint được chuẩn hóa frontmatter và bổ sung hướng dẫn tương thích Codex.

## Danh mục

| Nhóm | Phiên bản nguồn | Skill |
| --- | --- | --- |
| engineering | 1.2.0 | architecture, code-review, debug, deploy-checklist, documentation, incident-response, standup, system-design, tech-debt, testing-strategy |
| product-management | 1.2.0 | competitive-brief, metrics-review, product-brainstorming, roadmap-update, sprint-planning, stakeholder-update, synthesize-research, write-spec |
| research-desk | 0.4.1 | citation-check, decision-matrix, llm-council, paper-compare, paper-critique, related-work, research-litnote |
| learning-framework | 0.2.0 | active-recall, chunking, deep-work, deliberate-practice, evergreen-notes, feynman-technique, interleaving, learn, metalearning, pomodoro-and-focus, second-brain-para, spaced-repetition, zettelkasten |
| research-superpowers | 0.41.1 | acquire-sources, add-to-library, brainstorming-research, drafting-manuscript, drift-report, executing-research-plan, finishing-a-research-project, grant-finder, ingest-source, literature-review, requesting-peer-review, scaffold-research-project, semantic-wiki-review, using-research-powers, wiki-graph, wiki-lint, writing-research-plan |
| research-integrity | 1.5.0 | research-integrity |
| documents | synced | pdf, docx, pptx, xlsx |

## Giới hạn và phần thay thế

- `skill-creator`: Codex already provides its native skill-creator.
- `docs`: Requires Claude document tools; use the existing Codex Pages skills when a Page is requested.
- `google-workspace`: Requires Claude-specific connector tooling; discover actual available tools for Google tasks.
- `import-memory`: Requires Claude memory-write tools.
- `morning`: Personal briefing and scheduling tools are outside this project migration.
- `trash-and-marketplace`: Deleted skills and marketplace catalog entries are not installed user workflows.
- `learning-output-style`: SessionStart hook preserved only as optional learning guidance in CODEX.md; no automatic pause or code placeholders.
- `mcp-and-hooks`: Original manifests retained as reference only. No MCP endpoint or lifecycle hook has been activated.

Đây là chuyển workflow global, chưa kích hoạt kết nối MCP hoặc hook. Lệnh brainstorm cũ thuộc Product Management được bao phủ bởi skill `product-brainstorming`; các agent nguồn là tài liệu vai trò, không tự đăng ký thành agent Codex.

## Kiểm tra và sử dụng

Đã kiểm tra 60/60 skill bằng validator `skill-creator`, xác nhận mọi symlink global trỏ đúng tài nguyên và kiểm tra cú pháp Python của helper bằng AST; không chạy pipeline, hook hoặc dịch vụ bên ngoài trong migration này. Dependency của helper và kết nối MCP phải được kiểm tra khi có nhiệm vụ sử dụng thực tế.

Phiên hiện tại có thể đọc trực tiếp skill qua đường dẫn trong danh mục. Mở lại phiên Codex để môi trường quét danh sách skill global mới. Trước khi tiếp tục dự án, đọc PRD, kế hoạch, review, principles và đối chiếu kết quả C2/C3 mới nhất; không coi ghi chú trạng thái cũ là kết quả kiểm thử mới.

Cấu trúc discovery theo [tài liệu OpenAI về workflow trong repo](https://developers.openai.com/blog/skills-agents-sdk).

`AGENTS.md` là cấu hình riêng của dự án. Không cài skill vào `.agents/skills` của repo; tài nguyên dùng chung đã được chuyển ra ngoài repo. Skill hệ thống sẵn có của Codex được giữ nguyên.
