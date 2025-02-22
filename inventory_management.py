import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from xpinyin import Pinyin

# 新增销售记录文件路径
SALES_HISTORY_PATH = "销售历史.xlsx"
EXCEL_PATH = "商品资料.xlsx"


def load_data():
    try:
        return pd.read_excel(EXCEL_PATH, dtype={'条码': str})
    except FileNotFoundError:
        columns = ['名称（必填）', '分类（必填）', '条码', '库存量', '进货价（必填）', '销售价（必填）',
                   '毛利率', '批发价', '会员价', '会员折扣', '积分商品', '生产日期',
                   '保质期', '拼音码', '创建日期']
        return pd.DataFrame(columns=columns)


def save_data(df):
    df.to_excel(EXCEL_PATH, index=False)


def generate_pinyin(name):
    p = Pinyin()
    return p.get_initials(name, '')[:10].lower()

def purchase_mode():
    st.subheader("商品入库管理")
    # 初始化输入状态
    if 'purchase_input' not in st.session_state:
        st.session_state.purchase_input = ""

    # 使用on_change处理输入
    def on_purchase_input():
        barcode = st.session_state.purchase_input.strip()
        if barcode:
            df = load_data()
            match = df[df['条码'] == barcode]

            if not match.empty:
                df.loc[df['条码'] == barcode, '库存量'] += 1
                save_data(df)
                st.success(f"已更新库存：{match.iloc[0]['名称（必填）']} 当前库存：{match.iloc[0]['库存量'] + 1}")
                st.session_state.purchase_input = ""  # 清空输入
            else:
                st.session_state.new_product_barcode = barcode
                st.session_state.purchase_input = ""  # 清空输入
                st.rerun()

    # 输入框绑定session_state
    st.text_input("请扫描商品条码（入库）",
                  key="purchase_input",
                  on_change=on_purchase_input)

    if 'new_product_barcode' in st.session_state:
        with st.form("new_product_form"):
            st.write("新增商品登记")
            name = st.text_input("商品名称（必填）")
            category = st.selectbox("商品分类", ["零食", "饮料", "日用品"])
            purchase_price = st.number_input("进货价（必填）", min_value=0.0)
            sale_price = st.number_input("销售价（必填）", min_value=0.0)

            if st.form_submit_button("确认添加"):
                new_product = {
                    '名称（必填）': name,
                    '分类（必填）': category,
                    '条码': st.session_state.new_product_barcode,
                    '库存量': 1,
                    '进货价（必填）': purchase_price,
                    '销售价（必填）': sale_price,
                    '拼音码': generate_pinyin(name),
                    '创建日期': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                df = load_data()
                df = pd.concat([df, pd.DataFrame([new_product])], ignore_index=True)
                save_data(df)
                del st.session_state.new_product_barcode
                st.rerun()


# 加载销售历史数据
def load_sales_history():
    """加载销售历史数据"""
    try:
        df = pd.read_excel(SALES_HISTORY_PATH, dtype={'条码': str}, parse_dates=['销售时间'])
        # 数据清洗
        df['数量'] = df['数量'].astype(int)
        df['销售额'] = df['销售额'].astype(float)
        df['利润'] = df['利润'].astype(float)
        return df
    except FileNotFoundError:
        columns = ['销售时间', '条码', '名称', '数量', '进货价', '销售价', '销售额', '利润']
        return pd.DataFrame(columns=columns)


def save_sales_history(new_records):
    """保存销售记录"""
    if os.path.exists(SALES_HISTORY_PATH):
        df = load_sales_history()
    else:
        df = pd.DataFrame(columns=['销售时间', '条码', '名称', '数量', '进货价', '销售价', '销售额', '利润'])

    df = pd.concat([df, pd.DataFrame(new_records)], ignore_index=True)
    df.to_excel(SALES_HISTORY_PATH, index=False)


# 销售模式函数
def sale_mode():
    st.subheader("商品销售")

    # 初始化购物车（使用字典结构）
    if 'cart' not in st.session_state:
        st.session_state.cart = {}  # 格式：{条码: {quantity: 数量, info: 商品信息}}

    # 初始化输入状态
    if 'sale_input' not in st.session_state:
        st.session_state.sale_input = ""

    # 处理商品扫描
    def on_sale_input():
        barcode = st.session_state.sale_input.strip()
        if barcode:
            df = load_data()
            match = df[df['条码'] == barcode]

            if not match.empty:
                product = match.iloc[0].to_dict()
                current_stock = product['库存量']

                # 计算已存在购物车的数量
                cart_quantity = st.session_state.cart.get(barcode, {}).get('quantity', 0)
                requested_quantity = cart_quantity + 1

                # 实时库存校验（包含购物车中的预占数量）
                if requested_quantity > current_stock:
                    st.error(f"库存不足！当前库存：{current_stock}，已选数量：{cart_quantity}")
                    st.session_state.sale_input = ""
                    return

                # 更新购物车
                st.session_state.cart[barcode] = {
                    'quantity': requested_quantity,
                    'info': product
                }
                st.session_state.sale_input = ""

                # 实时显示更新后的数量
                st.rerun()
            else:
                st.error("未找到商品信息！")
                st.session_state.sale_input = ""

    st.text_input("请扫描商品条码（销售）", key="sale_input", on_change=on_sale_input)

    # 显示购物车
    if st.session_state.cart:
        st.write("当前购物车：")
        cart_items = []
        total = 0
        for barcode, item in st.session_state.cart.items():
            product = item['info']
            quantity = item['quantity']
            subtotal = product['销售价（必填）'] * quantity
            cart_items.append({
                "名称": product['名称（必填）'],
                "单价": product['销售价（必填）'],
                "数量": quantity,
                "小计": subtotal,
                "最大可购": product['库存量']  # 显示当前实际库存
            })
            total += subtotal

        # 显示带库存信息的表格
        df_cart = pd.DataFrame(cart_items)
        st.dataframe(df_cart.style.apply(
            lambda x: ['background: lightyellow' if x['数量'] > x['最大可购'] else '' for _ in x],
            axis=1
        ))

        st.write(f"总金额：{total:.2f} 元")

        # 结算按钮带双重校验
        if st.button("完成结算", type="primary"):
            df = load_data()
            try:
                # 生成销售记录
                sales_records = []
                sale_time = datetime.now()

                for barcode, item in st.session_state.cart.items():
                    product = df[df['条码'] == barcode].iloc[0]
                    quantity = item['quantity']

                    # 生成单条记录
                    record = {
                        '销售时间': sale_time,
                        '条码': barcode,
                        '名称': product['名称（必填）'],
                        '数量': quantity,
                        '进货价': product['进货价（必填）'],
                        '销售价': product['销售价（必填）'],
                        '销售额': product['销售价（必填）'] * quantity,
                        '利润': (product['销售价（必填）'] - product['进货价（必填）']) * quantity
                    }
                    sales_records.append(record)

                # 保存销售记录
                save_sales_history(sales_records)

                # 执行库存扣减
                for barcode, item in st.session_state.cart.items():
                    df.loc[df['条码'] == barcode, '库存量'] -= item['quantity']

                save_data(df)
                st.session_state.cart = {}
                st.success("结算成功！")
                st.rerun()
            except ValueError as e:
                st.error(f"结算失败：{str(e)}")
                st.session_state.cart = {}
                st.rerun()

    # 添加购物车管理功能
    if st.session_state.cart:
        with st.expander("购物车管理"):
            for barcode in list(st.session_state.cart.keys()):
                col1, col2, col3 = st.columns([4, 2, 1])
                with col1:
                    st.write(f"{st.session_state.cart[barcode]['info']['名称（必填）']}")
                with col2:
                    product_info = st.session_state.cart[barcode]['info']
                    new_qty = st.number_input(
                        "数量",
                        min_value=0,
                        max_value=int(product_info['库存量']),
                        value=int(st.session_state.cart[barcode]['quantity']),
                        key=f"qty_{barcode}"
                    )
                    if new_qty != st.session_state.cart[barcode]['quantity']:
                        st.session_state.cart[barcode]['quantity'] = new_qty
                        st.rerun()
                with col3:
                    if st.button("删除", key=f"del_{barcode}"):
                        del st.session_state.cart[barcode]
                        st.rerun()


# 销售历史分析模块
def sales_history_mode():
    st.subheader("销售历史分析")

    # 日期范围选择
    end_date = datetime.today()
    start_date = end_date - timedelta(days=30)

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("开始日期", start_date)
    with col2:
        end_date = st.date_input("结束日期", end_date)

    # 加载数据
    df = load_sales_history()
    if df.empty:
        st.warning("暂无销售记录")
        return

    # 筛选数据
    mask = (df['销售时间'].dt.date >= start_date) & (df['销售时间'].dt.date <= end_date)
    filtered_df = df[mask]

    if filtered_df.empty:
        st.warning("选定时间段内无销售记录")
        return

    # 显示统计指标
    total_sales = filtered_df['销售额'].sum()
    total_profit = filtered_df['利润'].sum()

    st.metric("总销售额", f"¥{total_sales:.2f}")
    st.metric("总利润", f"¥{total_profit:.2f}")

    # 显示原始数据
    with st.expander("查看详细记录"):
        st.dataframe(filtered_df.sort_values('销售时间', ascending=False))

    # 生成每日趋势数据
    daily_df = filtered_df.set_index('销售时间').resample('D').agg({
        '销售额': 'sum',
        '利润': 'sum'
    }).reset_index()
    daily_df['日期'] = daily_df['销售时间'].dt.date

    # 绘制趋势图表
    tab1, tab2 = st.tabs(["销售额趋势", "利润趋势"])

    with tab1:
        st.line_chart(daily_df, x='日期', y='销售额', use_container_width=True)

    with tab2:
        st.line_chart(daily_df, x='日期', y='利润', use_container_width=True)

    # 添加数据导出
    if st.button("导出当前筛选数据"):
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="下载CSV",
            data=csv,
            file_name=f"sales_{start_date}_{end_date}.csv",
            mime='text/csv'
        )


# 主函数
def main():
    st.title("商品库存管理系统")

    # 修改模式选择
    mode = st.sidebar.radio("选择模式",
                            ["销售模式", "入库模式", "销售历史"],
                            on_change=lambda: [st.session_state.pop(k, None) for k in ['cart', 'new_product_barcode']])

    if mode == "销售模式":
        sale_mode()
    elif mode == "入库模式":
        purchase_mode()
    else:
        sales_history_mode()

    # 显示当前库存
    st.sidebar.subheader("当前库存概览")
    df = load_data()
    st.sidebar.dataframe(df[['名称（必填）', '库存量']].sort_values('库存量', ascending=False))


if __name__ == "__main__":
    main()
