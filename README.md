# Air Quality Dashboard for German Cities

This project automatically collects air quality data from major German cities and creates an interactive dashboard with charts and maps using the Datawrapper API.

## Features

- 🌍 Real-time air quality data from 10 major German cities
- 📊 Interactive charts showing AQI, PM2.5, PM10, NO2, O3, SO2, and CO levels
- 🗺️ Map visualization of air quality across Germany
- 📈 Historical trend analysis
- 🔄 Automated updates every 6 hours via GitHub Actions
- 🌐 Hosted on GitHub Pages

## Setup Instructions

### 1. Fork this repository

### 2. Set up API Keys as GitHub Secrets

Go to your repository Settings → Secrets and variables → Actions, and add these secrets:

- `NINJA_API_KEY`: Your API key from [API Ninjas](https://api.api-ninjas.com/)
- `DATAWRAPPER_API_TOKEN`: Your API token from [Datawrapper](https://www.datawrapper.de/)

### 3. Enable GitHub Pages

1. Go to repository Settings → Pages
2. Under "Source", select "GitHub Actions"
3. Save the settings

### 4. Enable GitHub Actions

1. Go to the Actions tab in your repository
2. If prompted, enable GitHub Actions for your repository
3. The workflow will run automatically every 6 hours, or you can trigger it manually

### 5. Access your dashboard

After the first successful workflow run, your dashboard will be available at:
`https://[your-username].github.io/[repository-name]/`

## Manual Deployment

To run the script locally:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export NINJA_API_KEY="your_ninja_api_key"
   export DATAWRAPPER_API_TOKEN="your_datawrapper_token"
   ```

3. Run the script:
   ```bash
   python datawrapper.py
   ```

## Data Sources

- **Air Quality Data**: [API Ninjas Air Quality API](https://api.api-ninjas.com/api/airquality)
- **Visualization**: [Datawrapper](https://www.datawrapper.de/)

## Cities Monitored

- Berlin
- Hamburg
- Munich
- Cologne
- Frankfurt
- Stuttgart
- Düsseldorf
- Dortmund
- Essen
- Leipzig

## License

This project is open source and available under the MIT License.
