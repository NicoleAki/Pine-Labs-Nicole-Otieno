"""
Category-Level Metrics Dashboard
---------------------------------
Run with:  streamlit run dashboard.py

Expects a CSV named 'deduped_copy3.csv' in the same folder (or upload one
via the sidebar), with at minimum these columns:
main_category, sub_category, discounted_price, actual_price,
discount_percentage, rating, rating_count

To export from your notebook:
    deduped_copy3.to_csv('deduped_copy3.csv', index=False)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Category Metrics Dashboard", layout="wide")

# Data loading
st.sidebar.header("Data")
uploaded = st.sidebar.file_uploader("Upload deduped_copy3.csv", type="csv")

@st.cache_data
def load_data(file):
    return pd.read_csv(file)

if uploaded is not None:
    df = load_data(uploaded)
else:
    try:
        df = load_data("deduped_copy3.csv")
        st.sidebar.success("Loaded deduped_copy3.csv from local folder.")
    except FileNotFoundError:
        st.warning(
            "No data found. Please upload `deduped_copy3.csv` using the "
            "sidebar, or place it in the same folder as script."
        )
        st.stop()

required_cols = {"main_category", "discounted_price", "actual_price",
                  "discount_percentage", "rating", "rating_count", "log_rating_count"}
missing = required_cols - set(df.columns)
if missing:
    st.error(f"Dataset is missing required columns: {missing}")
    st.stop()

# Sidebar filters
st.sidebar.header("Filters")
categories = sorted(df["main_category"].dropna().unique())
selected_categories = st.sidebar.multiselect(
    "Main category", categories, default=categories
)
filtered = df[df["main_category"].isin(selected_categories)]

# Header
st.title("Category-Level Metrics Dashboard")
st.markdown(
    """
This dashboard walks through how **price, discount, and customer rating**
relate to each other across product categories in the dataset. Use the
sidebar to focus on specific categories.
"""
)

# Section 1: Overview
st.header("1. Catalogue Overview")
st.markdown(
    """
The catalogue is dominated by a small number of large categories.
**Electronics**, **Home & Kitchen**, and **Computers & Accessories**
together account for the large majority of products — everything else
is a long tail of small, thinly-populated categories. Keep this in mind
when comparing category averages below: metrics for a category with
only 1–2 products are far less reliable than metrics for a category
with hundreds.
"""
)

col1, col2, col3 = st.columns(3)
col1.metric("Total products", f"{len(filtered):,}")
col2.metric("Categories shown", f"{filtered['main_category'].nunique()}")
col3.metric("Avg. rating", f"{filtered['rating'].mean():.2f}")

counts = filtered["main_category"].value_counts().sort_values(ascending=True)
fig_counts = px.bar(
    counts, orientation="h",
    labels={"value": "Number of products", "index": "Main category"},
    title="Products per Category"
)
st.plotly_chart(fig_counts, use_container_width=True)

# Section 2: Price and Discount by Category
st.header("2. Price and Discount by Category")
st.markdown(
    """
Median prices vary sharply by category — some categories (like Office
Products) are inherently low-cost, while others (Electronics) span a
much wider and higher price range. Discount depth also differs: some
categories are discounted far more heavily than others on average,
which is worth knowing before assuming a discount strategy applies
evenly across the whole catalogue.
"""
)

price_summary = (
    filtered.groupby("main_category")
    .agg(
        total_products=("main_category", "count"),
        median_actual_price=("actual_price", "median"),
        median_discounted_price=("discounted_price", "median"),
        avg_discount_percentage=("discount_percentage", "mean"),
    )
    .sort_values("total_products", ascending=False)
)
st.dataframe(price_summary.style.format({
    "median_actual_price": "₹{:.0f}",
    "median_discounted_price": "₹{:.0f}",
    "avg_discount_percentage": "{:.1%}",
}))

fig_discount = px.bar(
    price_summary.reset_index(),
    x="main_category", y="avg_discount_percentage",
    title="Average Discount Percentage by Category",
    labels={"avg_discount_percentage": "Avg. Discount %", "main_category": "Category"},
)
fig_discount.update_yaxes(tickformat=".0%")
st.plotly_chart(fig_discount, use_container_width=True)

# Section 3: Discount vs Rating
st.header("3. Does a Bigger Discount Mean a Better Rating?")
st.markdown(
    """
The scatter plot below is the key story of this dashboard: **discount
percentage shows no clear relationship with rating.** Points are spread
across the full discount range at almost every rating level — heavily
discounted products are rated just as unpredictably as lightly
discounted ones. If anything, the least-discounted category
(Office Products) tends to carry some of the higher ratings, the
opposite of what a "discount drives satisfaction" story would predict.
"""
)

fig_scatter = px.scatter(
    filtered, x="rating", y="discount_percentage", color="main_category",
    opacity=0.6, hover_data=["product_name"] if "product_name" in filtered.columns else None,
    labels={"discount_percentage": "Discount %", "rating": "Rating"},
    title="Discount Percentage vs Rating"
)
fig_scatter.update_yaxes(tickformat=".0%")
st.plotly_chart(fig_scatter, use_container_width=True)

# Section 4: Rating Distribution
st.header("4. Rating Distribution")
st.markdown(
    """
Ratings are heavily clustered near the top of the scale. Most products
sit between 3.8 and 4.5, and very few products fall below 3.0. This
matters for interpretation: with so little spread in the data, even a
"typical" product looks highly rated, and there's limited room for any
model or metric to meaningfully separate "good" from "great."
"""
)

frac_high = (filtered["rating"] >= 4.0).mean()
st.metric("Share of products rated 4.0 or above", f"{frac_high:.1%}")

fig_hist = px.histogram(
    filtered, x="rating", nbins=20,
    title="Distribution of Ratings",
    labels={"rating": "Rating"}
)
st.plotly_chart(fig_hist, use_container_width=True)

# Section 5: Popularity vs Rating
st.header("5. Popularity vs Rating")
st.markdown(
    """
Does having more reviews mean a product is better rated? Not really.
Plotted on a log scale (since review counts vary enormously, from a
handful to hundreds of thousands), popularity and rating show no
strong upward trend — a product with very few ratings can score just
as well as one with tens of thousands. The one pattern worth noting:
products with **very few** ratings tend to cluster at the lower end of
the rating scale, suggesting a product needs some minimum level of
engagement before it can reach the highest ratings — but beyond that
baseline, more popularity doesn't push ratings any higher.
"""
)

filtered_pop = filtered[filtered["rating_count"] > 0].copy()
fig_pop = px.scatter(
    filtered_pop, x="rating", y="rating_count", color="main_category",
    log_y=True, opacity=0.6,
    labels={"rating_count": "Rating Count (log scale)", "rating": "Rating"},
    title="Rating Count (log scale) vs Rating"
)
st.plotly_chart(fig_pop, use_container_width=True)

# Footer
st.markdown("---")
st.caption(
    "Dashboard built with Streamlit and Plotly. Data reflects a cleaned, "
    "deduplicated snapshot of the product catalogue."
)