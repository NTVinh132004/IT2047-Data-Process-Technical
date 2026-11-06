# Slide báo cáo trên sample

Bộ slide gồm 20 trang theo sườn Mở đầu, Chương 1–5; dùng số liệu sample 2019 đã đối soát ngày 31/10/2026 và kết quả
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

| Trang | Phần | Nội dung | Trọng tâm nói |
| --- | --- | --- | --- |
| 1 | | Tiêu đề, học viên, giảng viên | Một câu về bài toán |
| 2–4 | Mở đầu | Lý do chọn đề tài, bài toán, mục tiêu và phạm vi | Đầu vào → xử lý → đầu ra; 5 câu hỏi Q1–Q5; phạm vi bộ mẫu (R-38) |
| 5–7 | Chương 1 | Lakehouse và Delta Lake, Data Vault 2.0, công nghệ | Satellite chỉ thêm khi `hash_diff` đổi; Delta = Parquet + nhật ký giao dịch |
| 8–9 | Chương 2 | Bộ dữ liệu, vấn đề dữ liệu → yêu cầu thiết kế | Quý khởi tạo khác quý báo cáo; dữ liệu bị sửa ở đợt sau |
| 10–13 | Chương 3 | Kiến trúc, kỹ thuật nạp TXT → landing → Bronze, Raw Vault, BV/PIT/Gold | Mỗi tầng một job Airflow; landing phân vùng tháng (TN7) |
| 14–18 | Chương 4 | Kiểm chứng, TN1, TN2/TN4/TN6, kết quả Q1–Q5 | Trung vị 3 lần đo; mỗi thực nghiệm có phép kiểm đúng; không diễn giải nhân quả |
| 19 | Chương 5 | Kết quả, hạn chế, hướng phát triển | Không suy rộng hiệu năng sang bộ đầy đủ |
| 20 | | Demo và hỏi đáp | Airflow → control.layer_run → CORR1/PIT → PostgreSQL → notebook |

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

Thông tin học viên khai báo đầu file `scripts/build_sample_slides.py` (`STUDENT`, `STUDENT_ID`, `ADVISOR`); điền tên giảng viên vào `ADVISOR` rồi chạy `uv run python -m scripts.build_sample_slides`, hoặc sửa thẳng trong PowerPoint.
