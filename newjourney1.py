import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static

def load_and_process_data(data_text):
    # Split the text into lines and parse each line
    lines = data_text.strip().split('\n')
    cleaned_data = []
    
    for line in lines:
        parts = line.split('\t')
        timestamp = datetime.strptime(parts[1], '%Y-%m-%d %H:%M:%S.%f')
        latitude = float(parts[2])
        longitude = float(parts[3])
        
        record = {
            'timestamp': timestamp,
            'latitude': latitude,
            'longitude': longitude,
            'date': timestamp.date(),
            'time': timestamp.strftime('%H:%M:%S'),
            'hour': timestamp.hour,
            'minute': timestamp.minute
        }
        cleaned_data.append(record)
    
    df = pd.DataFrame(cleaned_data)
    
    # Add derived columns
    df['duration_minutes'] = ((df['timestamp'] - df['timestamp'].iloc[0]).dt.total_seconds() / 60).round(2)
    
    # Calculate speeds and distances
    df['distance_km'] = 0.0
    for i in range(1, len(df)):
        coords_1 = (df['latitude'].iloc[i-1], df['longitude'].iloc[i-1])
        coords_2 = (df['latitude'].iloc[i], df['longitude'].iloc[i])
        df.loc[df.index[i], 'distance_km'] = geodesic(coords_1, coords_2).kilometers
    
    df['cumulative_distance'] = df['distance_km'].cumsum()
    df['speed_kmh'] = df['distance_km'] / (10/60)  # 10 minutes between readings converted to hours
    
    return df

def create_map(df):
    center_lat = df['latitude'].mean()
    center_lon = df['longitude'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
    
    # Add route line
    coordinates = [[row['latitude'], row['longitude']] for index, row in df.iterrows()]
    folium.PolyLine(coordinates, weight=2, color='blue', opacity=0.8).add_to(m)
    
    # Add start and end markers
    folium.Marker(
        [df['latitude'].iloc[0], df['longitude'].iloc[0]],
        popup='Start',
        icon=folium.Icon(color='green')
    ).add_to(m)
    
    folium.Marker(
        [df['latitude'].iloc[-1], df['longitude'].iloc[-1]],
        popup='End',
        icon=folium.Icon(color='red')
    ).add_to(m)
    
    return m

def main():
    st.title("Journey Analysis Dashboard")
    
    # Your data text here (the content from the file)
    data_text = """0_Austin_Los Angeles	2024-07-09 04:27:31.270921	30.267115	-97.743072
    # ... (rest of the data)
    """
    
    df = load_and_process_data(data_text)
    
    st.header("1. Journey Overview")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Duration", f"{df['duration_minutes'].max()/60:.1f} hours")
    with col2:
        st.metric("Total Distance", f"{df['cumulative_distance'].max():.1f} km")
    with col3:
        st.metric("Average Speed", f"{df['speed_kmh'].mean():.1f} km/h")
    
    st.header("2. Route Visualization")
    st.write("Interactive map showing the journey route:")
    folium_static(create_map(df))
    
    st.header("3. Speed Analysis")
    fig_speed = px.line(df, x='timestamp', y='speed_kmh', title='Speed over Time')
    st.plotly_chart(fig_speed)
    
    # Identify potential issues and improvements
    st.header("4. Journey Insights and Recommendations")
    
    # Speed variations
    speed_std = df['speed_kmh'].std()
    high_speed_segments = df[df['speed_kmh'] > df['speed_kmh'].mean() + speed_std]
    low_speed_segments = df[df['speed_kmh'] < df['speed_kmh'].mean() - speed_std]
    
    with st.expander("Speed Pattern Analysis"):
        st.write("Analysis of speed patterns and potential improvements:")
        st.write(f"- Speed consistency (std dev): {speed_std:.2f} km/h")
        st.write(f"- Number of high-speed segments: {len(high_speed_segments)}")
        st.write(f"- Number of low-speed segments: {len(low_speed_segments)}")
        
        if len(high_speed_segments) > 0:
            st.write("⚠️ Consider more consistent speeds for better fuel efficiency")
    
    # Time analysis
    with st.expander("Time Efficiency Analysis"):
        morning_rush = df[(df['hour'] >= 7) & (df['hour'] <= 9)]
        evening_rush = df[(df['hour'] >= 16) & (df['hour'] <= 18)]
        
        if len(morning_rush) > 0:
            st.write("🕒 Journey intersects with morning rush hour")
        if len(evening_rush) > 0:
            st.write("🕕 Journey intersects with evening rush hour")
        
        st.write("Recommendations:")
        st.write("- Consider adjusting departure time to avoid rush hours")
        st.write("- Plan breaks during peak traffic times")
    
    # Route efficiency
    with st.expander("Route Efficiency Analysis"):
        straight_line_distance = geodesic(
            (df['latitude'].iloc[0], df['longitude'].iloc[0]),
            (df['latitude'].iloc[-1], df['longitude'].iloc[-1])
        ).kilometers
        
        route_efficiency = straight_line_distance / df['cumulative_distance'].max()
        st.write(f"Route Efficiency Score: {route_efficiency:.2%}")
        
        if route_efficiency < 0.8:
            st.write("📍 Consider more direct routes where possible")
    
    st.header("5. Environmental Impact")
    # Assuming average fuel consumption of 8L/100km
    fuel_consumption = df['cumulative_distance'].max() * 0.08
    co2_emissions = fuel_consumption * 2.31  # kg CO2 per liter
    
    st.metric("Estimated CO2 Emissions", f"{co2_emissions:.1f} kg")
    
    with st.expander("Environmental Recommendations"):
        st.write("Ways to reduce environmental impact:")
        st.write("1. Maintain consistent speed to optimize fuel efficiency")
        st.write("2. Service vehicle regularly for optimal performance")
        st.write("3. Consider using an electric vehicle for future journeys")
        st.write("4. Plan routes to minimize distance and avoid congestion")

if __name__ == "__main__":
    main()
