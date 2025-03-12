import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import altair as alt
from urllib.error import URLError
import re

# Set page configuration
st.set_page_config(
    page_title="Congressional Legislation Dashboard",
    page_icon="🏛️",
    layout="wide"
)

# Define your API key here (or use environment variables in production)
API_KEY = "unrdj3eDQReaMA62Vbl3V4jKHhJy74TZjAey3deh"  # Replace with your actual API key

# Cache data to improve performance
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_recent_bills(congress, chamber, limit=25, offset=0):
    """Fetch recent bills from the Congress.gov API"""
    url = f"https://api.congress.gov/v3/bill/{congress}/{chamber.lower()}?api_key={API_KEY}&limit={limit}&offset={offset}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Process bills data
        if not data or "bills" not in data:
            return []
        
        processed_bills = []
        for bill in data.get("bills", []):
            sponsors = []
            if "sponsors" in bill and len(bill["sponsors"]) > 0:
                sponsors = [sponsor.get("name", "") for sponsor in bill["sponsors"]]
            
            cosponsors_count = 0
            if "cosponsors" in bill and "count" in bill["cosponsors"]:
                cosponsors_count = bill["cosponsors"]["count"]
            
            # Extract party from sponsor (if available)
            sponsor_party = ""
            if "sponsors" in bill and len(bill["sponsors"]) > 0:
                if "party" in bill["sponsors"][0]:
                    sponsor_party = bill["sponsors"][0]["party"]
            
            processed_bills.append({
                "bill_number": bill.get("number", ""),
                "title": bill.get("title", ""),
                "congress": bill.get("congress", ""),
                "introduced_date": bill.get("introducedDate", ""),
                "latest_action_date": bill.get("latestAction", {}).get("actionDate", ""),
                "latest_action_text": bill.get("latestAction", {}).get("text", ""),
                "bill_type": bill.get("type", ""),
                "bill_url": bill.get("url", ""),
                "sponsors": ", ".join(sponsors),
                "sponsor_party": sponsor_party,
                "cosponsors_count": cosponsors_count,
                "bill_id": bill.get("number", "").replace(" ", ""),
            })
        
        return processed_bills
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching bill data: {e}")
        return []

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_bill_subjects(congress, bill_type, bill_number):
    """Fetch subjects for a specific bill"""
    url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{bill_number}?api_key={API_KEY}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        subjects = []
        if "bill" in data and "subjects" in data["bill"] and "legislativeSubjects" in data["bill"]["subjects"]:
            subjects = data["bill"]["subjects"]["legislativeSubjects"]
        
        return subjects
        
    except requests.exceptions.RequestException as e:
        # Don't show error since this is a supplemental call
        return []

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_bill_actions(congress, bill_type, bill_number):
    """Fetch actions for a specific bill"""
    url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{bill_number}/actions?api_key={API_KEY}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        actions = []
        if "actions" in data:
            actions = data["actions"]
        
        processed_actions = []
        for action in actions:
            processed_actions.append({
                "date": action.get("actionDate", ""),
                "text": action.get("text", ""),
                "type": action.get("type", ""),
                "chamber": action.get("actionChamber", ""),
                "is_vote": "vote" in action.get("type", "").lower()
            })
        
        return processed_actions
        
    except requests.exceptions.RequestException as e:
        # Don't show error since this is a supplemental call
        return []

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_bill_votes(congress, bill_type, bill_number):
    """Fetch votes for a specific bill"""
    url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{bill_number}/votes?api_key={API_KEY}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        votes = []
        if "votes" in data:
            votes = data["votes"]
        
        processed_votes = []
        for vote in votes:
            # Extract total vote counts
            total_yes = 0
            total_no = 0
            total_present = 0
            total_not_voting = 0
            
            dem_yes = 0
            dem_no = 0
            rep_yes = 0
            rep_no = 0
            
            if "total" in vote:
                if "yea" in vote["total"]:
                    total_yes = vote["total"]["yea"]
                if "no" in vote["total"]:
                    total_no = vote["total"]["no"]
                if "present" in vote["total"]:
                    total_present = vote["total"]["present"]
                if "notVoting" in vote["total"]:
                    total_not_voting = vote["total"]["notVoting"]
            
            # Extract party breakdown if available
            if "democratic" in vote:
                if "yea" in vote["democratic"]:
                    dem_yes = vote["democratic"]["yea"]
                if "no" in vote["democratic"]:
                    dem_no = vote["democratic"]["no"]
            
            if "republican" in vote:
                if "yea" in vote["republican"]:
                    rep_yes = vote["republican"]["yea"]
                if "no" in vote["republican"]:
                    rep_no = vote["republican"]["no"]
            
            processed_votes.append({
                "date": vote.get("date", ""),
                "question": vote.get("question", ""),
                "result": vote.get("result", ""),
                "total_yes": total_yes,
                "total_no": total_no,
                "total_present": total_present,
                "total_not_voting": total_not_voting,
                "dem_yes": dem_yes,
                "dem_no": dem_no,
                "rep_yes": rep_yes,
                "rep_no": rep_no,
                "vote_chamber": vote.get("chamber", ""),
                "vote_id": vote.get("rollNumber", "")
            })
        
        return processed_votes
        
    except requests.exceptions.RequestException as e:
        # Don't show error since this is a supplemental call
        return []

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_bill_text(congress, bill_type, bill_number):
    """Fetch text versions for a specific bill"""
    url = f"https://api.congress.gov/v3/bill/{congress}/{bill_type}/{bill_number}/text?api_key={API_KEY}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        text_versions = []
        if "textVersions" in data:
            text_versions = data["textVersions"]
        
        processed_texts = []
        for text in text_versions:
            processed_texts.append({
                "date": text.get("date", ""),
                "type": text.get("type", ""),
                "url": text.get("formats", [{}])[0].get("url", "") if "formats" in text and len(text["formats"]) > 0 else ""
            })
        
        return processed_texts
        
    except requests.exceptions.RequestException as e:
        # Don't show error since this is a supplemental call
        return []

def parse_bill_number(bill_number):
    """Parse bill number into type and number components"""
    match = re.match(r"([A-Za-z]+)(\d+)", bill_number)
    if match:
        bill_type = match.group(1).lower()
        number = match.group(2)
        return bill_type, number
    return None, None

def get_party_color(party):
    """Get the color associated with a political party"""
    if party == 'D':
        return "#3182ce"  # Democrat blue
    elif party == 'R':
        return "#e53e3e"  # Republican red
    else:
        return "#718096"  # Independent gray

def main():
    # Add custom CSS
    st.markdown("""
    <style>
    .party-democrat {
        color: #3182ce;
        font-weight: bold;
    }
    .party-republican {
        color: #e53e3e;
        font-weight: bold;
    }
    .bill-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
        border-left: 4px solid #718096;
    }
    .bill-card-democrat {
        border-left: 4px solid #3182ce;
    }
    .bill-card-republican {
        border-left: 4px solid #e53e3e;
    }
    .vote-info {
        margin-top: 20px;
        padding: 15px;
        border-radius: 5px;
        background-color: #f8f9fa;
    }
    .tab-subheader {
        font-size: 16px;
        font-weight: bold;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Title and description
    st.title("Congressional Legislation Dashboard")
    st.markdown("""
    Explore bills, voting records, and legislative activity in the U.S. Congress. 
    This dashboard provides insights into recent congressional activity, party-line voting, 
    and the legislative process.
    """)
    
    # Current Congress number (would be dynamically calculated in production)
    current_congress = 117
    
    # Sidebar for controls
    with st.sidebar:
        st.header("Filter Options")
        
        # Congress selection
        congress_options = [current_congress, current_congress-1, current_congress-2]
        congress = st.selectbox(
            "Select Congress",
            options=congress_options,
            format_func=lambda x: f"{x}th Congress ({2019 + 2*(x-116)}-{2021 + 2*(x-116)})"
        )
        
        # Chamber selection
        chamber = st.radio("Select Chamber", ["House", "Senate"])
        
        # Bill type filter
        bill_type_options = ["All Types", "HR (House Bill)", "S (Senate Bill)", "HJRES (House Joint Resolution)", "SJRES (Senate Joint Resolution)"]
        bill_type_filter = st.selectbox("Bill Type", bill_type_options)
        
        # Party filter
        party_filter = st.radio("Sponsor Party", ["All", "Democrats", "Republicans"])
        
        # Status filter
        status_options = ["All Statuses", "Introduced", "Passed House", "Passed Senate", "Became Law", "Failed"]
        status_filter = st.selectbox("Bill Status", status_options)
        
        # Load button
        load_bills = st.button("Load Bills", type="primary")
    
    # Only load bills when explicitly requested to avoid API rate limits
    if load_bills:
        # Fetch bills based on filters
        with st.spinner(f"Loading bills from the {congress}th Congress ({chamber})..."):
            bills = fetch_recent_bills(congress, chamber, limit=50)
        
        if not bills:
            st.error("No bills found that match your criteria.")
            st.info("Try changing your filters or try again later.")
            return
        
        # Convert to DataFrame for easier filtering
        bills_df = pd.DataFrame(bills)
        
        # Apply filters
        if bill_type_filter != "All Types":
            bill_type_code = bill_type_filter.split(" ")[0]
            bills_df = bills_df[bills_df['bill_number'].str.contains(bill_type_code, case=False)]
        
        if party_filter != "All":
            party_code = "D" if party_filter == "Democrats" else "R"
            bills_df = bills_df[bills_df['sponsor_party'] == party_code]
        
        if status_filter != "All Statuses":
            if status_filter == "Introduced":
                bills_df = bills_df[bills_df['latest_action_text'].str.contains("Introduced|Read twice", case=False, na=False)]
            elif status_filter == "Passed House":
                bills_df = bills_df[bills_df['latest_action_text'].str.contains("Passed House|Passed.*House", case=False, na=False)]
            elif status_filter == "Passed Senate":
                bills_df = bills_df[bills_df['latest_action_text'].str.contains("Passed Senate|Passed.*Senate", case=False, na=False)]
            elif status_filter == "Became Law":
                bills_df = bills_df[bills_df['latest_action_text'].str.contains("Became Public Law|Signed by President", case=False, na=False)]
            elif status_filter == "Failed":
                bills_df = bills_df[bills_df['latest_action_text'].str.contains("Failed|Vetoed", case=False, na=False)]
        
        # Sort by introduced date (most recent first)
        if 'introduced_date' in bills_df.columns:
            bills_df['introduced_date'] = pd.to_datetime(bills_df['introduced_date'], errors='coerce')
            bills_df = bills_df.sort_values('introduced_date', ascending=False)
        
        # Display overview metrics
        st.header("Legislative Overview")
        
        metrics_cols = st.columns(4)
        
        with metrics_cols[0]:
            st.metric("Total Bills", len(bills_df))
        
        with metrics_cols[1]:
            dem_sponsored = len(bills_df[bills_df['sponsor_party'] == 'D'])
            st.metric("Democrat Sponsored", dem_sponsored, f"{dem_sponsored/len(bills_df)*100:.1f}%" if len(bills_df) > 0 else "0%")
        
        with metrics_cols[2]:
            rep_sponsored = len(bills_df[bills_df['sponsor_party'] == 'R'])
            st.metric("Republican Sponsored", rep_sponsored, f"{rep_sponsored/len(bills_df)*100:.1f}%" if len(bills_df) > 0 else "0%")
        
        with metrics_cols[3]:
            # Calculate average cosponsors
            avg_cosponsors = bills_df['cosponsors_count'].mean()
            st.metric("Avg. Cosponsors", f"{avg_cosponsors:.1f}")
        
        # Party breakdown visualization
        party_counts = bills_df['sponsor_party'].value_counts().reset_index()
        party_counts.columns = ['party', 'count']
        
        # Create pie chart for party breakdown
        if not party_counts.empty:
            st.subheader("Bill Sponsorship by Party")
            
            fig_party = px.pie(
                party_counts, 
                values='count', 
                names='party',
                color='party',
                color_discrete_map={'D': '#3182ce', 'R': '#e53e3e', '': '#718096'},
                title="Bills Sponsored by Party"
            )
            
            fig_party.update_traces(textinfo='percent+label')
            fig_party.update_layout(height=400)
            
            st.plotly_chart(fig_party, use_container_width=True)
            
            # Add legislative narrative
            if dem_sponsored > rep_sponsored:
                st.markdown(f"**Democrats** have sponsored **{dem_sponsored}** bills ({dem_sponsored/len(bills_df)*100:.1f}%) in this congress, compared to **{rep_sponsored}** bills ({rep_sponsored/len(bills_df)*100:.1f}%) sponsored by **Republicans**. This reflects the Democratic majority in the {chamber}.")
            elif rep_sponsored > dem_sponsored:
                st.markdown(f"**Republicans** have sponsored **{rep_sponsored}** bills ({rep_sponsored/len(bills_df)*100:.1f}%) in this congress, compared to **{dem_sponsored}** bills ({dem_sponsored/len(bills_df)*100:.1f}%) sponsored by **Democrats**. This reflects the Republican majority in the {chamber}.")
            else:
                st.markdown(f"Both parties have sponsored an equal number of bills in this congress, with **{dem_sponsored}** bills each.")
        
        # Create a tab layout for different bill views
        tab_list, tab_detail, tab_votes = st.tabs(["Bill List", "Bill Details", "Voting Analysis"])
        
        with tab_list:
            # Bill list view
            st.header(f"Recent Bills in the {congress}th Congress ({chamber})")
            
            if bills_df.empty:
                st.info("No bills found matching your filters.")
            else:
                # Display bills as cards
                for _, bill in bills_df.iterrows():
                    # Determine party style
                    party_class = ""
                    if bill['sponsor_party'] == 'D':
                        party_class = "bill-card-democrat"
                    elif bill['sponsor_party'] == 'R':
                        party_class = "bill-card-republican"
                    
                    # Format date
                    intro_date = bill['introduced_date']
                    if isinstance(intro_date, pd.Timestamp):
                        intro_date = intro_date.strftime("%B %d, %Y")
                    
                    st.markdown(
                        f"""
                        <div class="bill-card {party_class}">
                            <h3>{bill['bill_number']}: {bill['title']}</h3>
                            <p><strong>Introduced:</strong> {intro_date}</p>
                            <p><strong>Sponsor:</strong> {bill['sponsors']}</p>
                            <p><strong>Latest Action:</strong> {bill['latest_action_text']} ({bill['latest_action_date']})</p>
                            <p><strong>Cosponsors:</strong> {bill['cosponsors_count']}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
        
        with tab_detail:
            st.header("Bill Details")
            
            if bills_df.empty:
                st.info("No bills found matching your filters.")
            else:
                # Create a selectbox for bill selection
                bill_options = [f"{bill['bill_number']}: {bill['title'][:50]}..." for _, bill in bills_df.iterrows()]
                selected_bill_index = st.selectbox("Select a bill for detailed information", range(len(bill_options)), format_func=lambda i: bill_options[i])
                
                if selected_bill_index is not None:
                    selected_bill = bills_df.iloc[selected_bill_index]
                    
                    # Display bill information
                    st.subheader(f"{selected_bill['bill_number']}")
                    st.markdown(f"### {selected_bill['title']}")
                    
                    # Format dates
                    intro_date = selected_bill['introduced_date']
                    if isinstance(intro_date, pd.Timestamp):
                        intro_date = intro_date.strftime("%B %d, %Y")
                    
                    latest_action_date = selected_bill['latest_action_date']
                    if isinstance(latest_action_date, pd.Timestamp):
                        latest_action_date = latest_action_date.strftime("%B %d, %Y")
                    
                    # Bill info in columns
                    bill_info_cols = st.columns(2)
                    
                    with bill_info_cols[0]:
                        st.markdown(f"**Introduced:** {intro_date}")
                        st.markdown(f"**Sponsor:** {selected_bill['sponsors']}")
                        st.markdown(f"**Sponsor Party:** {selected_bill['sponsor_party']}")
                    
                    with bill_info_cols[1]:
                        st.markdown(f"**Latest Action:** {selected_bill['latest_action_text']}")
                        st.markdown(f"**Action Date:** {latest_action_date}")
                        st.markdown(f"**Cosponsors:** {selected_bill['cosponsors_count']}")
                    
                    # Extract bill type and number for API calls
                    bill_type, bill_number = parse_bill_number(selected_bill['bill_number'])
                    
                    if bill_type and bill_number:
                        # Fetch additional bill information
                        with st.spinner("Loading bill details..."):
                            bill_subjects = fetch_bill_subjects(congress, bill_type, bill_number)
                            bill_actions = fetch_bill_actions(congress, bill_type, bill_number)
                            bill_texts = fetch_bill_text(congress, bill_type, bill_number)
                        
                        # Show subjects
                        if bill_subjects:
                            st.markdown("#### Bill Subjects")
                            subject_list = ", ".join([subject.get("name", "") for subject in bill_subjects])
                            st.markdown(subject_list)
                        
                        # Show bill text links
                        if bill_texts:
                            st.markdown("#### Bill Text Versions")
                            for text in bill_texts:
                                text_date = text.get("date", "")
                                if text_date:
                                    try:
                                        text_date = datetime.strptime(text_date, "%Y-%m-%d").strftime("%B %d, %Y")
                                    except:
                                        pass
                                
                                st.markdown(f"[{text.get('type', '')} ({text_date})]({text.get('url', '')})")
                        
                        # Show bill action timeline
                        if bill_actions:
                            st.markdown("#### Legislative Timeline")
                            
                            # Convert to DataFrame for easier manipulation
                            actions_df = pd.DataFrame(bill_actions)
                            
                            # Convert dates
                            if 'date' in actions_df.columns:
                                actions_df['date'] = pd.to_datetime(actions_df['date'], errors='coerce')
                                actions_df = actions_df.sort_values('date', ascending=True)
                            
                            # Display as timeline
                            for _, action in actions_df.iterrows():
                                date_str = action['date'].strftime("%B %d, %Y") if isinstance(action['date'], pd.Timestamp) else action['date']
                                
                                # Highlight votes differently
                                if action['is_vote']:
                                    st.markdown(f"**{date_str}** - 🗳️ **VOTE**: {action['text']} ({action['chamber']})")
                                else:
                                    st.markdown(f"**{date_str}** - {action['text']} ({action['chamber']})")
                    else:
                        st.error("Could not parse bill number for detailed information.")
        
        with tab_votes:
            st.header("Voting Analysis")
            
            if bills_df.empty:
                st.info("No bills found matching your filters.")
            else:
                # Create a selectbox for bill selection
                vote_bill_options = [f"{bill['bill_number']}: {bill['title'][:50]}..." for _, bill in bills_df.iterrows()]
                vote_selected_bill_index = st.selectbox("Select a bill to analyze votes", range(len(vote_bill_options)), format_func=lambda i: vote_bill_options[i])
                
                if vote_selected_bill_index is not None:
                    vote_selected_bill = bills_df.iloc[vote_selected_bill_index]
                    
                    # Display bill title
                    st.subheader(f"{vote_selected_bill['bill_number']}")
                    st.markdown(f"### {vote_selected_bill['title']}")
                    
                    # Extract bill type and number for API calls
                    bill_type, bill_number = parse_bill_number(vote_selected_bill['bill_number'])
                    
                    if bill_type and bill_number:
                        # Fetch votes for this bill
                        with st.spinner("Loading voting data..."):
                            bill_votes = fetch_bill_votes(congress, bill_type, bill_number)
                        
                        if bill_votes:
                            # Convert to DataFrame
                            votes_df = pd.DataFrame(bill_votes)
                            
                            # Sort by date
                            if 'date' in votes_df.columns:
                                votes_df['date'] = pd.to_datetime(votes_df['date'], errors='coerce')
                                votes_df = votes_df.sort_values('date', ascending=False)
                            
                            # Create tabs for each vote
                            vote_tabs = st.tabs([f"Vote {i+1}: {vote['date'].strftime('%b %d, %Y') if isinstance(vote['date'], pd.Timestamp) else vote['date']}" 
                                               for i, vote in enumerate(bill_votes)])
                            
                            for i, (vote_tab, vote) in enumerate(zip(vote_tabs, bill_votes)):
                                with vote_tab:
                                    # Format date
                                    vote_date = vote['date']
                                    if isinstance(vote_date, str):
                                        try:
                                            vote_date = datetime.strptime(vote_date, '%Y-%m-%d').strftime('%B %d, %Y')
                                        except:
                                            pass
                                    elif isinstance(vote_date, pd.Timestamp):
                                        vote_date = vote_date.strftime('%B %d, %Y')
                                    
                                    # Vote information
                                    st.markdown(f"**Date:** {vote_date}")
                                    st.markdown(f"**Chamber:** {vote['vote_chamber']}")
                                    st.markdown(f"**Question:** {vote['question']}")
                                    st.markdown(f"**Result:** {vote['result']}")
                                    
                                    # Vote counts
                                    vote_cols = st.columns(4)
                                    
                                    with vote_cols[0]:
                                        st.metric("Yea", vote['total_yes'])
                                    
                                    with vote_cols[1]:
                                        st.metric("Nay", vote['total_no'])
                                    
                                    with vote_cols[2]:
                                        st.metric("Present", vote['total_present'])
                                    
                                    with vote_cols[3]:
                                        st.metric("Not Voting", vote['total_not_voting'])
                                    
                                    # Visualize results
                                    st.subheader("Vote Results")
                                    
                                    # Overall results pie chart
                                    vote_results = {
                                        'Category': ['Yea', 'Nay', 'Present', 'Not Voting'],
                                        'Count': [vote['total_yes'], vote['total_no'], vote['total_present'], vote['total_not_voting']]
                                    }
                                    
                                    vote_results_df = pd.DataFrame(vote_results)
                                    
                                    fig_vote = px.pie(
                                        vote_results_df,
                                        values='Count',
                                        names='Category',
                                        color='Category',
                                        color_discrete_map={
                                            'Yea': '#4CAF50',
                                            'Nay': '#F44336',
                                            'Present': '#9E9E9E',
                                            'Not Voting': '#BDBDBD'
                                        },
                                        title="Overall Vote Results"
                                    )
                                    
                                    fig_vote.update_traces(textinfo='percent+label')
                                    
                                    st.plotly_chart(fig_vote, use_container_width=True)
                                    
                                    # Party breakdown visualization
                                    if vote['dem_yes'] > 0 or vote['dem_no'] > 0 or vote['rep_yes'] > 0 or vote['rep_no'] > 0:
                                        st.subheader("Vote by Party")
                                        
                                        # Create data for party breakdown
                                        party_vote_data = {
                                            'Party': ['Democrats', 'Democrats', 'Republicans', 'Republicans'],
                                            'Vote': ['Yea', 'Nay', 'Yea', 'Nay'],
                                            'Count': [vote['dem_yes'], vote['dem_no'], vote['rep_yes'], vote['rep_no']]
                                        }
                                        
                                        party_vote_df = pd.DataFrame(party_vote_data)
                                        
                                        # Stacked bar chart for party breakdown
                                        fig_party_vote = px.bar(
                                            party_vote_df,
                                            x='Party',
                                            y='Count',
                                            color='Vote',
                                            barmode='stack',
                                            color_discrete_map={'Yea': '#4CAF50', 'Nay': '#F44336'},
                                            title="Votes by Party"
                                        )
                                        
                                        fig_party_vote.update_layout(height=400)
                                        
                                        st.plotly_chart(fig_party_vote, use_container_width=True)
                                        
                                        # Calculate party line voting
                                        dem_total = vote['dem_yes'] + vote['dem_no']
                                        rep_total = vote['rep_yes'] + vote['rep_no']
                                        
                                        dem_yea_pct = vote['dem_yes'] / dem_total * 100 if dem_total > 0 else 0
                                        rep_yea_pct = vote['rep_yes'] / rep_total * 100 if rep_total > 0 else 0
                                        
                                        # Narrative about party-line voting
                                        st.markdown("#### Party Voting Analysis")
                                        
                                        if abs(dem_yea_pct - rep_yea_pct) > 50:
                                            st.markdown("🔥 **Highly partisan vote**")
                                            st.markdown(f"This was a clear party-line vote with **{dem_yea_pct:.1f}%** of Democrats and **{rep_yea_pct:.1f}%** of Republicans voting 'Yea'.")
                                            
                                            if (dem_yea_pct > 50 and rep_yea_pct < 50) or (dem_yea_pct < 50 and rep_yea_pct > 50):
                                                st.markdown("The parties took opposite positions on this legislation.")
                                        elif abs(dem_yea_pct - rep_yea_pct) > 20:
                                            st.markdown("🔄 **Moderately partisan vote**")
                                            st.markdown(f"This vote showed some partisan division with **{dem_yea_pct:.1f}%** of Democrats and **{rep_yea_pct:.1f}%** of Republicans voting 'Yea'.")
                                        else:
                                            st.markdown("🤝 **Bipartisan vote**")
                                            st.markdown(f"This was a bipartisan vote with **{dem_yea_pct:.1f}%** of Democrats and **{rep_yea_pct:.1f}%** of Republicans voting 'Yea'.")
                                            
                                            if dem_yea_pct > 70 and rep_yea_pct > 70:
                                                st.markdown("Strong bipartisan support suggests this was a consensus issue.")
                                            
                                        # Add interpretation based on outcome
                                        if vote['result'].lower() == 'passed' or 'agreed to' in vote['result'].lower():
                                            if dem_yea_pct > 50 and rep_yea_pct < 50:
                                                st.markdown("This bill passed primarily with **Democratic support**.")
                                            elif dem_yea_pct < 50 and rep_yea_pct > 50:
                                                st.markdown("This bill passed primarily with **Republican support**.")
                                            elif dem_yea_pct > 50 and rep_yea_pct > 50:
                                                st.markdown("This bill received support from **both parties**.")
                                        
                                        # Vote solidarity
                                        party_solidarity = st.columns(2)
                                        
                                        with party_solidarity[0]:
                                            st.metric("Democratic Unity", f"{max(dem_yea_pct, 100-dem_yea_pct):.1f}%")
                                        
                                        with party_solidarity[1]:
                                            st.metric("Republican Unity", f"{max(rep_yea_pct, 100-rep_yea_pct):.1f}%")
                                    else:
                                        st.info("No party breakdown available for this vote.")
                        else:
                            st.info("No voting data available for this bill.")
                    else:
                        st.error("Could not parse bill number for voting analysis.")
    
    # Footer with data source information
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666;">
        <p>Data sourced from the Library of Congress Congress.gov API. Updated as of March 2025.</p>
        <p>This dashboard is for educational and transparency purposes.</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()