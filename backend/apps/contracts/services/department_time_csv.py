import csv
import io
from datetime import date, timedelta


def generate_department_time_csv(tenant, year: int, month: int) -> tuple[bytes, str]:
    from dateutil.relativedelta import relativedelta

    from apps.core.context import Context
    from config.schema import schema

    date_from = date(year, month, 1)
    date_to = (date_from + relativedelta(months=1)) - timedelta(days=1)

    admin_user = tenant.users.filter(is_admin=True).first()
    if not admin_user:
        admin_user = tenant.users.first()

    class FakeRequest:
        headers = {}

    ctx = Context(request=FakeRequest(), user=admin_user)

    result = schema.execute_sync(
        """
        query($dateFrom: Date!, $dateTo: Date!) {
            departmentTimeAnalysis(dateFrom: $dateFrom, dateTo: $dateTo) {
                costDistribution {
                    departmentName
                    ftes
                    percentage
                    cost
                }
            }
        }
        """,
        variable_values={"dateFrom": str(date_from), "dateTo": str(date_to)},
        context_value=ctx,
    )

    if result.errors:
        raise ValueError(f"Query failed: {result.errors}")

    rows = result.data["departmentTimeAnalysis"]["costDistribution"] or []

    buf = io.StringIO()
    buf.write("\ufeff")
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(["Department", "FTEs", "%", "Cost"])
    for r in rows:
        writer.writerow([
            r["departmentName"],
            f"{r['ftes']:.2f}",
            f"{r['percentage']:.1f}",
            f"{r['cost']:.2f}",
        ])

    filename = f"department-time-{year}-{month:02d}.csv"
    return buf.getvalue().encode("utf-8"), filename
