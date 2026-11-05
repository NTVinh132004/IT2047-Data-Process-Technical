# Slide báo cáo trên sample

Bộ slide gồm 20 trang, dùng số liệu sample 2019 đã đối soát ngày 31/10/2026 và kết quả
thực nghiệm C5 trên sample (R-38, `experiments/results/`). Báo cáo chính:
[bao-cao-do-an.md](bao-cao-do-an.md).

## Mở sản phẩm

- [PowerPoint có 8 chart chỉnh sửa được](../data/reports/sample-report/bao-cao-sample.pptx).
- [PDF để đọc nhanh](../data/reports/sample-report/bao-cao-sample.pdf).
- [HTML để trình chiếu trong trình duyệt](../data/reports/sample-report/bao-cao-sample.html): phím trái/phải chuyển trang, F để toàn màn hình.
- [Nội dung và ghi chú thuyết trình](../data/reports/sample-report/slide-outline.json).
- [Số liệu gốc tổng hợp](../data/reports/sample-report/metrics.json), có SHA-256 nguồn và phiên bản Delta.

File PowerPoint, PDF và HTML được sinh từ cùng mô tả bố cục/nội dung; PDF không
phải bản export bằng PowerPoint/LibreOffice. PowerPoint được kiểm cấu trúc XML;
bản PDF/preview được kiểm bố cục. Cần mở kiểm tra lại trong Office đang dùng
trước buổi trình bày vì font/chart renderer có thể khác môi trường tạo file.

## Trình tự trình bày

| Trang | Nội dung | Trọng tâm nói |
| --- | --- | --- |
| 1–4 | Bài toán, kết quả chính và dữ liệu | 50.000 loan; 1.934.614 loan-month; CORR1 là 20 dòng sửa giả lập riêng |
| 5–6 | Kiến trúc và kỹ thuật nạp TXT → landing → Bronze | Đọc text rồi tách trường; landing phân vùng tháng; `replaceWhere` theo kỳ; số đo TN7 |
| 7–9 | Cổng chất lượng, Raw Vault, `load_date` | Hard rule trước, soft rule sau; chỉ chèn khi `hash_diff` đổi; `load_date` giả lập theo tháng |
| 10–11 | Kiểm chứng MVP và FR-14 | 69/69 kiểm tra C0–C4; SCD1 không đại diện mọi mô hình chiều |
| 12–14 | Thực nghiệm TN1, TN2, TN4, TN6 | Trung vị 3 lần; mỗi thực nghiệm có phép kiểm đúng; không suy rộng sang bộ đầy đủ |
| 15–19 | Kết quả Q1–Q5 | Luôn nêu mẫu số; phân nhóm gộp dùng loan-month; không diễn giải nhân quả |
| 20 | Kết luận, giới hạn, demo | Mở `experiments/results/` và JSON cổng khi được hỏi |

Khung trình bày gợi ý 20–25 phút; rút ngắn phần kiến trúc nếu học phần yêu cầu
ít thời gian hơn. Ghi chú theo từng slide nằm trong PowerPoint và file outline.

## Tái sinh

Khi sample PostgreSQL đang chạy và mart đã công bố, dùng:

```bash
make report-sample
```

Lệnh kiểm đếm TXT và đọc Delta log/PostgreSQL; không nạp lại pipeline, không
chạy historical. Nó tạo metrics và dựng slide; các trang thực nghiệm đọc
`experiments/results/` (sinh bằng `make experiments`, `make experiment-charts`).
Báo cáo `docs/bao-cao-do-an.md` là văn bản biên tập tay, lệnh này không ghi đè.
Dữ liệu/output nằm dưới `data/` đã được ignore; source script và docs mới là
phần lưu trong Git. Không đưa file loan-level vào slide hoặc thư mục bàn giao.

## Nghiệm thu còn thiếu

Video demo và thông tin học viên/giảng viên, mẫu bìa theo học phần do người thực hiện
hoàn thiện; không tự suy ra danh tính từ tài khoản máy. Trạng thái các cổng xem
`tests/gates/results/` và Kế hoạch mục 6.
