-- Lát perf của các tháng truyền qua var months (giả lập dữ liệu đến theo đợt)
select *
from raw.perf
where reporting_period in ({{ var('months') | join(', ') }})
