#!/usr/bin/env python3
"""
财务日历演示数据种子脚本

规则（与截图一致）：
  - 财年从上一自然年 10 月开始，到当年 9 月结束
xx
  - 财年起始日 = 10月1日当周或之前最日
  - 每财周 7 天（周日 ~ 周六）

  - 每财年 52 

：
    python scripts/seed_fidar.py

或指定 API 地址：
    API_BASE_URL=http://localhost:8000 pythar.py
"""

import os
imp sys
ta

try:
    import
except ImportError:

    sys.exit(1)

# =======================
# 配置
# ==========================================================

)
IMPORT_URL = f"{API_BASE_URL}/api/fiscal-calendar/import"

# 4-4-5 财月周数分配（每财季 13 周，共 4 财季 = 52 周）


# 生成哪些财年
FISCAL_YEARS = [2024, 2025,


# ============================================================================
# 财务日历生成逻辑
#=====

def get_fiscal_year_start(fiscal_yea
    """
    获取财年起始日期。

    规则：财年从上一自然年 10 月 1 日当周或之前最近开始。
    例：FY2026 → 找 2025-10-01 当周的周日
日）
    """
    oct1 = date(fiscal_year - 1, 1)
    # weekday(): 0=Mon ... 6=Sun
7 天
% 7
    return oct1 - timedelta(days=days_back)



    """
    获取财年结束日期（下一财年起始日前一天）。
    用于判3 周。
    """
    return get_fiscal_year_start(fisca


[dict]:
 """
    生成指定财年的完整财务日历数据。

    财月标签使用 P1~P12（与截FY{year}。
。
    """
    rec
    fy_start = g
    fy_end = get_fiscal_year_end(fiscal_year)
    fy_label = f"FY{fiscal_year}"

    fw_num = 1
rt

    for quarter_idx in range(4):  # FQ1~F
        fq_label = f"FQ{quarter_idx + 1}"
P10

        for weeks_in_month in WEEKS_PER_MONN_QUARTER:
}"

            for _ in range(weeks_in_month):
                fw_label = f"FW{fw_num:02d}"
                fw_start = current_date


                records.append({
w_label,
                    "fw_start_da
                    "fw_end_date": fw_endt(),
                    "fiscal_month": fm_label,
                    "fiscal_quarter": fq_label,
                    "fiscal_year": fy_label,
                    "natural_year": fw_start.ye
                })

                cu
= 1

 1


    if current_datnd:

te
        fw_end = fw_start + timedelta(days=6)
        records.append({
            "fw_label": fw_label,
,
            "fw_e(),
            "fi
            "fiscal_quarter": "FQ4",
            "fiscal_year": fy_label,
            "natural_year": fw_start.year,
        })

    return records


# =====
# 导入逻辑
# =========================================

def import_records(records: list[dict], fiscal_y> bool:
    """将财务日历记录批量导入到 API，返回 True 表示成功。""
    print(f"\n📅 正在导入 {fiscal_year}（共 {len(records)）...")

    # 打印预览
    print(f"   📋 数据预览（前3条 + 后3条）：")
    sa3:]
 mple:


            f"  {r['fiscal_month']:4s}  {r['fiscal_quarter']:4s}  {r['fiscal_y']}"
        )



    try
        resp = requesost(
,
            json=payload,
       "},
            timeout=30,
)
    except reError:
        print(f"   ❌ 无法连接到 {IMPORT_URL}")
        print）")
        return False
    except requests.exceptions.Timeout:
        print(f"   ❌ 请求超时，请检查后端服务状态")
e


        
        print(f"   ✅ 导入成功：新增 ")
        if data.get("er"):
            print(f"   ⚠️败：")
            for err in data["errors"][:5]:
                print(f
        re
    else:
        print(f"   ❌ 导入失败（HTTP {resp.stat300]}")
        return False


# =======================================
# 验证逻辑（本地计算，不调用 API）
=====

def verify_against_screensts():
    """
    验证生成结果是否与截图一致。
    截图关键数据点：
      FY2024: P1 起始 2023-10-01（周日）
      FY2025: P1 起始 2024-09-29（周日）
      FY2026: P1 起始
    """
    expected = {
        2024: date(2 1),
29),
,
    }
    print("\n🔍 验证财年起始日期（
    all_ok = True
    for fy, exp_start in expected.items():
        actual = getfy)
        ok = axp_start
        status = "✅" if ok else "❌"
        print(f"   {status} FY{fy}: 期望 {exp_start}，实际 {actual}")
        i
False



# ============================================================================
数
# =============

def main():
    print("=" * 60)
    print("  财务日历演示数据种子脚本（10月起始财年，周
    print(" 60)
")

# 先本地验证
    if not verify_against_screenshot
        print("\n❌ 财年起始日期验证失败，请检查生成逻辑")
        sys.exit(1)

    all_success = True

    for fiscal_year in FISCAL_YEARS:
        fy_label = f"FYear}"
        records = generate_fiscar)

        if cess:
            all_suce

    print()
    if all_success:
        print("✅ 所有财务日历数据导入完成！")
        print()
        print("   可通过以下方式验证：")
        p")
        print(f"   curl '{API_BASE_URL}/a
    else:

1)


n()
mai
    __":in "__ma ==if __name__