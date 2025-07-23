import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# Page configuration
st.set_page_config(
    page_title="HealthKart Influencer Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSV files with error handling
@st.cache_data
def load_data():
    try:
        influencers = pd.read_csv("influencers.csv")
        posts = pd.read_csv("posts.csv")
        tracking = pd.read_csv("tracking_data.csv")
        payouts = pd.read_csv("payouts.csv")
        return influencers, posts, tracking, payouts, None
    except FileNotFoundError as e:
        return None, None, None, None, f"File not found: {e.filename}"
    except Exception as e:
        return None, None, None, None, f"Error loading data: {str(e)}"

# Load data
influencers, posts, tracking, payouts, error = load_data()

if error:
    st.error(f"❌ {error}")
    st.info("Please ensure all CSV files (influencers.csv, posts.csv, tracking_data.csv, payouts.csv) are in the same directory as this script.")
    st.stop()

# Title and description
st.title("📊 HealthKart Influencer Campaign Dashboard")
st.markdown("Track and analyze influencer campaign performance, ROI, and payouts")

# Sidebar filters
st.sidebar.header("🔍 Filter Options")

# Platform filter
if "platform" in influencers.columns:
    platform_options = influencers["platform"].dropna().unique()
    platform_filter = st.sidebar.multiselect(
        "Select Platforms:",
        platform_options,
        default=platform_options
    )
else:
    platform_filter = []
    st.sidebar.warning("No 'platform' column found in influencers data")

# Category filter
if "category" in influencers.columns:
    category_options = influencers["category"].dropna().unique()
    category_filter = st.sidebar.multiselect(
        "Select Categories:",
        category_options,
        default=category_options
    )
else:
    category_filter = []
    st.sidebar.warning("No 'category' column found in influencers data")

# Date range filter if tracking data has dates
if "date" in tracking.columns or "campaign_date" in tracking.columns:
    date_col = "date" if "date" in tracking.columns else "campaign_date"
    tracking[date_col] = pd.to_datetime(tracking[date_col], errors='coerce')
    date_range = st.sidebar.date_input(
        "Select Date Range:",
        value=(tracking[date_col].min(), tracking[date_col].max()),
        min_value=tracking[date_col].min(),
        max_value=tracking[date_col].max()
    )

# Apply filters
filtered_influencers = influencers.copy()

if platform_filter and "platform" in influencers.columns:
    filtered_influencers = filtered_influencers[
        filtered_influencers["platform"].isin(platform_filter)
    ]

if category_filter and "category" in influencers.columns:
    filtered_influencers = filtered_influencers[
        filtered_influencers["category"].isin(category_filter)
    ]

# Main dashboard layout
col1, col2, col3, col4 = st.columns(4)

# Key metrics
with col1:
    total_influencers = len(filtered_influencers)
    st.metric("Total Influencers", total_influencers)

with col2:
    if "follower_count" in filtered_influencers.columns:
        total_reach = filtered_influencers["follower_count"].sum()
        st.metric("Total Reach", f"{total_reach:,}")
    else:
        st.metric("Total Reach", "N/A")

with col3:
    total_revenue = tracking["revenue"].sum() if "revenue" in tracking.columns else 0
    st.metric("Total Revenue", f"₹{total_revenue:,.0f}")

with col4:
    total_orders = tracking["orders"].sum() if "orders" in tracking.columns else 0
    st.metric("Total Orders", f"{total_orders:,}")

# Top Influencers Section
st.header("🌟 Top Influencers")

if "follower_count" in filtered_influencers.columns:
    top_influencers = filtered_influencers.sort_values(
        by="follower_count", 
        ascending=False
    ).head(10)
    
    # Display as cards
    cols = st.columns(2)
    for idx, (_, influencer) in enumerate(top_influencers.iterrows()):
        with cols[idx % 2]:
            with st.container():
                st.subheader(f"@{influencer.get('username', influencer.get('name', 'Unknown'))}")
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write(f"**Platform:** {influencer.get('platform', 'N/A')}")
                    st.write(f"**Category:** {influencer.get('category', 'N/A')}")
                with col_b:
                    st.write(f"**Followers:** {influencer.get('follower_count', 0):,}")
                    if 'engagement_rate' in influencer:
                        st.write(f"**Engagement:** {influencer['engagement_rate']:.2%}")
else:
    st.dataframe(filtered_influencers.head(10))

# Performance Analysis
st.header("📈 Campaign Performance Analysis")

# Merge data for analysis
try:
    merged = tracking.merge(
        influencers, 
        on="influencer_id", 
        how="left"
    )
    
    if not posts.empty:
        merged = merged.merge(
            posts, 
            on="influencer_id", 
            how="left", 
            suffixes=("_tracking", "_post")
        )
    
    # ROAS Calculation with error handling
    if "revenue" in merged.columns and "orders" in merged.columns:
        # Avoid division by zero
        merged["cost"] = merged["orders"] * 100  # Assuming cost per order is 100
        merged["ROAS"] = np.where(
            merged["cost"] > 0, 
            merged["revenue"] / merged["cost"], 
            0
        )
        
        # ROAS Summary
        if not merged.empty:
            roas_summary = merged.groupby("influencer_id").agg({
                "ROAS": "mean",
                "revenue": "sum",
                "orders": "sum"
            }).reset_index()
            
            # Merge with influencer names
            if "username" in influencers.columns or "name" in influencers.columns:
                name_col = "username" if "username" in influencers.columns else "name"
                roas_summary = roas_summary.merge(
                    influencers[["influencer_id", name_col]], 
                    on="influencer_id"
                )
            
            roas_summary = roas_summary.sort_values(by="ROAS", ascending=False)
            
            # Display top performers
            st.subheader("🏆 Top Performing Campaigns (by ROAS)")
            
            # Create visualization
            if len(roas_summary) > 0:
                fig = px.bar(
                    roas_summary.head(10),
                    y=name_col if name_col in roas_summary.columns else "influencer_id",
                    x="ROAS",
                    title="Top 10 Influencers by ROAS",
                    orientation="h"
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(roas_summary.head(10))
        else:
            st.warning("No data available for ROAS calculation")
    else:
        st.warning("Revenue or orders data not available for ROAS calculation")
        
except Exception as e:
    st.error(f"Error in performance analysis: {str(e)}")

# Revenue and Orders Summary
st.header("📦 Revenue and Orders Summary")

if "revenue" in tracking.columns and "orders" in tracking.columns:
    campaign_summary = tracking.groupby("influencer_id").agg({
        "orders": "sum",
        "revenue": "sum"
    }).reset_index()
    
    # Add influencer names if available
    if "username" in influencers.columns or "name" in influencers.columns:
        name_col = "username" if "username" in influencers.columns else "name"
        campaign_summary = campaign_summary.merge(
            influencers[["influencer_id", name_col]], 
            on="influencer_id",
            how="left"
        )
    
    campaign_summary = campaign_summary.sort_values(by="revenue", ascending=False)
    
    # Revenue distribution chart
    if len(campaign_summary) > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            fig_revenue = px.pie(
                campaign_summary.head(10),
                values="revenue",
                names=name_col if name_col in campaign_summary.columns else "influencer_id",
                title="Revenue Distribution (Top 10)"
            )
            st.plotly_chart(fig_revenue, use_container_width=True)
        
        with col2:
            fig_orders = px.bar(
                campaign_summary.head(10),
                x=name_col if name_col in campaign_summary.columns else "influencer_id",
                y="orders",
                title="Orders by Influencer (Top 10)"
            )
            fig_orders.update_xaxes(tickangle=45)
            st.plotly_chart(fig_orders, use_container_width=True)
    
    st.dataframe(campaign_summary.head(10))
else:
    st.warning("Revenue or orders data not available")

# Payout Tracking
st.header("💰 Payout Tracking")

if not payouts.empty:
    # Payout summary with status
    payout_summary = payouts.sort_values(by="total_payout", ascending=False)
    
    # Add status indicators
    if "status" in payouts.columns:
        col1, col2 = st.columns(2)
        
        with col1:
            status_counts = payouts["status"].value_counts()
            fig_status = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Payout Status Distribution"
            )
            st.plotly_chart(fig_status, use_container_width=True)
        
        with col2:
            pending_amount = payouts[payouts["status"] == "pending"]["total_payout"].sum()
            paid_amount = payouts[payouts["status"] == "paid"]["total_payout"].sum()
            
            st.metric("Pending Payouts", f"₹{pending_amount:,.0f}")
            st.metric("Paid Amount", f"₹{paid_amount:,.0f}")
    
    st.dataframe(payout_summary)
else:
    st.warning("No payout data available")

# Export Section
st.header("📥 Export Data")

col1, col2, col3 = st.columns(3)

with col1:
    if 'roas_summary' in locals() and not roas_summary.empty:
        csv_roas = roas_summary.to_csv(index=False)
        st.download_button(
            "📊 Download ROAS Summary",
            csv_roas,
            "roas_summary.csv",
            "text/csv"
        )

with col2:
    if not payouts.empty:
        csv_payouts = payouts.to_csv(index=False)
        st.download_button(
            "💰 Download Payouts",
            csv_payouts,
            "payouts.csv",
            "text/csv"
        )

with col3:
    if 'campaign_summary' in locals() and not campaign_summary.empty:
        csv_campaign = campaign_summary.to_csv(index=False)
        st.download_button(
            "📦 Download Campaign Summary",
            csv_campaign,
            "campaign_summary.csv",
            "text/csv"
        )

# Footer
st.markdown("---")
st.markdown("*Dashboard last updated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "*")