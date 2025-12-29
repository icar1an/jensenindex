import React, { useState, useEffect } from 'react';

/**
 * JENSEN HUANG LEATHER JACKET INDEX
 * Bloomberg Terminal Clone for Alternative Data Analysis
 * 
 * Tracks leather jacket resale prices on Grailed and correlates
 * with NVDA stock performance. Because markets are efficient.
 */

const JensenIndex = () => {
  const [activeTab, setActiveTab] = useState('Inflection');
  const [timeRange, setTimeRange] = useState('3M');
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const tabs = ['Inflection', 'Jensen Correlation', 'Top Listings'];
  const timeRanges = ['1W', '1M', '3M', '6M', '1Y', 'Max'];

  // Fetch from real backend
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`${process.env.REACT_APP_API_URL || ''}/api/index`);
        if (!response.ok) throw new Error('Network response was not ok');
        const jsonData = await response.json();
        
        setData(jsonData);
      } catch (error) {
        console.error('Error fetching data:', error);
        // Ensure we have a basic structure even on error
        setData({
          ticker: "JHLJ",
          name: "Jensen Huang Leather Jacket Index",
          status: "error",
          alt_data_metrics: [],
          weekly_data: [],
          top_listings: [],
          last_updated: "N/A"
        });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await fetch(`${process.env.REACT_APP_API_URL || ''}/api/scrape`);
      // Re-fetch data after scrape
      const response = await fetch(`${process.env.REACT_APP_API_URL || ''}/api/index`);
      const jsonData = await response.json();
      if (jsonData.status !== 'seeding') {
        setData(jsonData);
      }
    } catch (error) {
      console.error('Error refreshing data:', error);
    } finally {
      setRefreshing(false);
    }
  };

  const formatValue = (val, options = {}) => {
    if (val === undefined || val === null) return '';
    const num = parseFloat(val);
    const formatted = options.decimals !== undefined 
      ? num.toFixed(options.decimals)
      : num.toFixed(2);
    
    if (options.colorCode) {
      if (num > 0) return { value: formatted, color: '#00ff00' };
      if (num < 0) return { value: formatted, color: '#ff4444' };
      return { value: formatted, color: '#ffffff' };
    }
    return formatted;
  };

  const ValueCell = ({ value, highlight, decimals = 2 }) => {
    const result = formatValue(value, { colorCode: true, decimals });
    let bgColor = 'transparent';
    
    if (highlight === 'yellow' && parseFloat(value) > 5) bgColor = '#8B8000';
    if (highlight === 'red') bgColor = parseFloat(value) < -5 ? '#8B0000' : 'transparent';
    if (highlight === 'green' && parseFloat(value) > 5) bgColor = '#006400';
    
    return (
      <td style={{ 
        color: result.color, 
        backgroundColor: bgColor,
        padding: '2px 8px',
        textAlign: 'right',
        fontFamily: 'monospace',
        fontSize: '12px',
        borderRight: '1px solid #333'
      }}>
        {result.value}
      </td>
    );
  };

  const JensenScoreBadge = ({ score }) => {
    let color = '#888888';
    let label = 'Low';
    
    if (score >= 20) { color = '#00ff00'; label = 'PEAK JENSEN'; }
    else if (score >= 10) { color = '#ffcc00'; label = 'High'; }
    else if (score >= 5) { color = '#ff9900'; label = 'Mid'; }
    
    return (
      <span style={{
        backgroundColor: color,
        color: '#000000',
        padding: '1px 6px',
        fontSize: '10px',
        fontWeight: 'bold',
        borderRadius: '2px',
      }}>
        {score} ({label})
      </span>
    );
  };

  if (loading) {
    return (
      <div style={{
        backgroundColor: '#000000',
        color: '#ff9900',
        fontFamily: 'monospace',
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '24px', marginBottom: '16px' }}>
            JHLJ INDEX
          </div>
          <div style={{ color: '#888888' }}>
            Correlating leather jacket prices with NVDA...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      backgroundColor: '#000000',
      color: '#ff9900',
      fontFamily: '"Consolas", "Monaco", monospace',
      fontSize: '12px',
      minHeight: '100vh',
      padding: '0',
      lineHeight: '1.4'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        padding: '4px 8px',
        borderBottom: '1px solid #333',
        backgroundColor: '#1a1a1a'
      }}>
        <span style={{ 
          color: '#ff9900', 
          fontWeight: 'bold',
          fontSize: '14px',
          marginRight: '12px'
        }}>
          JHLJ Index
        </span>
        <span style={{ 
          color: '#00ff00', 
          fontSize: '12px',
          marginRight: '16px',
          display: 'flex',
          alignItems: 'center',
          gap: '4px'
        }}>
          <span style={{ 
            width: '8px', 
            height: '8px', 
            backgroundColor: '#00ff00', 
            borderRadius: '50%',
            boxShadow: '0 0 5px #00ff00'
          }}></span>
          LIVE
        </span>
        <span style={{ 
          color: '#888888', 
          fontSize: '11px',
          marginRight: '16px'
        }}>
          NVDA: {data.nvda_display || '$142.87 ▲ 2.74%'}
        </span>
        <button 
          onClick={handleRefresh}
          disabled={refreshing}
          style={{
            backgroundColor: refreshing ? '#333' : '#003366',
            color: 'white',
            border: 'none',
            padding: '2px 12px',
            fontSize: '11px',
            cursor: refreshing ? 'not-allowed' : 'pointer',
            marginRight: '8px',
          }}
        >
          {refreshing ? 'SCRAPING...' : 'REFRESH LATEST'}
        </button>
        <button style={{
          backgroundColor: '#ff6600',
          color: 'white',
          border: 'none',
          padding: '2px 12px',
          fontSize: '11px',
          cursor: 'pointer',
          marginLeft: '0',
        }}>
          Export ▼
        </button>
      </div>

      {/* Tabs */}
      <div style={{
        display: 'flex',
        gap: '0',
        backgroundColor: '#0a0a0a',
        borderBottom: '1px solid #333'
      }}>
        {tabs.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              backgroundColor: activeTab === tab ? '#003366' : 'transparent',
              color: activeTab === tab ? '#ffffff' : '#6699cc',
              border: 'none',
              padding: '6px 16px',
              fontSize: '12px',
              cursor: 'pointer',
              borderRight: '1px solid #333'
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Title Row */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '8px 12px',
        borderBottom: '1px solid #333'
      }}>
        <h2 style={{
          color: '#ffffff',
          fontSize: '14px',
          fontWeight: 'normal',
          margin: 0
        }}>
          Jensen Huang Leather Jacket Index - Alternative Data Summary
        </h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: '#888888', fontSize: '11px' }}>
            {data.status === 'live' ? 'Real-time feed active' : 'Snapshot mode'} | Last data point: {data.last_updated}
          </span>
          <span style={{
            color: '#ff9900',
            fontSize: '11px',
            cursor: 'pointer',
          }}>
            ⓘ Methodology
          </span>
        </div>
      </div>

      <div style={{ display: 'flex' }}>
        {/* Main Content */}
        <div style={{ flex: 1, padding: '8px' }}>
          
          {activeTab === 'Inflection' && (
            <>
              {/* Alt Data Metrics Table */}
              <table style={{ 
                width: '100%', 
                borderCollapse: 'collapse',
                marginBottom: '16px'
              }}>
                <thead>
                  <tr style={{ backgroundColor: '#1a1a1a' }}>
                    <th style={{ textAlign: 'left', padding: '4px 8px', color: '#888888', fontWeight: 'normal', fontSize: '11px', borderBottom: '1px solid #444' }}>
                      Alt Data Metrics
                    </th>
                    <th colSpan={3} style={{ textAlign: 'center', padding: '4px', color: '#ff9900', fontWeight: 'normal', fontSize: '10px', borderBottom: '1px solid #444' }}>
                      Trailing Average
                    </th>
                    <th colSpan={3} style={{ textAlign: 'center', padding: '4px', color: '#ff9900', fontWeight: 'normal', fontSize: '10px', borderBottom: '1px solid #444' }}>
                      Period over Period % Chg
                    </th>
                  </tr>
                  <tr style={{ backgroundColor: '#1a1a1a' }}>
                    <th style={{ padding: '4px 8px', borderBottom: '1px solid #333' }}></th>
                    <th style={{ padding: '4px 8px', color: '#888888', fontSize: '10px', textAlign: 'right', borderBottom: '1px solid #333' }}>91d</th>
                    <th style={{ padding: '4px 8px', color: '#888888', fontSize: '10px', textAlign: 'right', borderBottom: '1px solid #333' }}>28d</th>
                    <th style={{ padding: '4px 8px', color: '#888888', fontSize: '10px', textAlign: 'right', borderBottom: '1px solid #333' }}>7d</th>
                    <th style={{ padding: '4px 8px', color: '#888888', fontSize: '10px', textAlign: 'right', borderBottom: '1px solid #333' }}>91d</th>
                    <th style={{ padding: '4px 8px', color: '#888888', fontSize: '10px', textAlign: 'right', borderBottom: '1px solid #333' }}>28d</th>
                    <th style={{ padding: '4px 8px', color: '#888888', fontSize: '10px', textAlign: 'right', borderBottom: '1px solid #333' }}>7d</th>
                  </tr>
                </thead>
                <tbody>
                  {data.alt_data_metrics && data.alt_data_metrics.length > 0 ? (
                    data.alt_data_metrics.map((metric, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #222' }}>
                        <td style={{ 
                          color: metric.highlighted ? '#ffcc00' : '#ffffff',
                          padding: '4px 8px',
                          fontSize: '11px'
                        }}>
                          {metric.name}
                        </td>
                        <td style={{ color: '#ffffff', padding: '2px 8px', textAlign: 'right', fontFamily: 'monospace', fontSize: '12px' }}>
                          {formatValue(metric.trailing91)}
                        </td>
                        <td style={{ color: '#ffffff', padding: '2px 8px', textAlign: 'right', fontFamily: 'monospace', fontSize: '12px' }}>
                          {formatValue(metric.trailing28)}
                        </td>
                        <td style={{ color: '#ffffff', padding: '2px 8px', textAlign: 'right', fontFamily: 'monospace', fontSize: '12px' }}>
                          {formatValue(metric.trailing7)}
                        </td>
                        <ValueCell value={metric.pop91} highlight={metric.highlighted ? 'yellow' : null} />
                        <ValueCell value={metric.pop28} highlight={metric.highlighted ? 'yellow' : null} />
                        <ValueCell value={metric.pop7} highlight={metric.highlighted ? 'yellow' : null} />
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="7" style={{ padding: '20px', textAlign: 'center', color: '#888888' }}>
                        Waiting for real data... Click 'REFRESH LATEST' to populate index.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>

              {/* Time Series Controls */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                marginBottom: '8px',
                padding: '8px',
                backgroundColor: '#0a0a0a',
                borderTop: '1px solid #333'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ color: '#888888', fontSize: '10px' }}>Metric</span>
                  <select style={{
                    backgroundColor: '#333333',
                    color: '#ffffff',
                    border: '1px solid #444',
                    padding: '2px 8px',
                    fontSize: '11px'
                  }}>
                    <option>Jacket Price vs NVDA</option>
                    <option>Jensen Score</option>
                    <option>Listings Volume</option>
                  </select>
                </div>
                
                <div style={{ display: 'flex', gap: '2px', marginLeft: 'auto' }}>
                  {timeRanges.map(range => (
                    <button
                      key={range}
                      onClick={() => setTimeRange(range)}
                      style={{
                        backgroundColor: timeRange === range ? '#ff9900' : '#333333',
                        color: timeRange === range ? '#000000' : '#888888',
                        border: 'none',
                        padding: '2px 8px',
                        fontSize: '10px',
                        cursor: 'pointer',
                        fontWeight: timeRange === range ? 'bold' : 'normal'
                      }}
                    >
                      {range}
                    </button>
                  ))}
                </div>
              </div>

              {/* Weekly Data Table */}
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#1a1a1a' }}>
                      <th style={{ textAlign: 'left', padding: '4px 8px', color: '#888888', fontWeight: 'normal', fontSize: '10px' }}>Week Ending</th>
                      <th style={{ textAlign: 'right', padding: '4px 8px', color: '#888888', fontWeight: 'normal', fontSize: '10px' }}>Jacket % Chg</th>
                      <th style={{ textAlign: 'right', padding: '4px 8px', color: '#888888', fontWeight: 'normal', fontSize: '10px' }}>NVDA % Chg</th>
                      <th style={{ textAlign: 'right', padding: '4px 8px', color: '#888888', fontWeight: 'normal', fontSize: '10px' }}>Jensen Score</th>
                      <th style={{ textAlign: 'right', padding: '4px 8px', color: '#888888', fontWeight: 'normal', fontSize: '10px' }}>Signal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.weekly_data && data.weekly_data.length > 0 ? (
                      data.weekly_data.map((row, idx) => {
                        const jacketNum = parseFloat(row.jacket);
                        const nvdaNum = parseFloat(row.nvda);
                        const aligned = (jacketNum > 0 && nvdaNum > 0) || (jacketNum < 0 && nvdaNum < 0);
                        
                        return (
                          <tr key={idx} style={{ borderBottom: '1px solid #222' }}>
                            <td style={{ color: '#ffffff', padding: '3px 8px' }}>{row.week}</td>
                            <ValueCell value={row.jacket} highlight={row.jacket > 4 ? 'yellow' : null} />
                            <ValueCell value={row.nvda} />
                            <td style={{ color: row.jensen > 7 ? '#00ff00' : '#ffffff', padding: '3px 8px', textAlign: 'right' }}>
                              {row.jensen ? row.jensen.toFixed(1) : '0.0'}
                            </td>
                            <td style={{ 
                              padding: '3px 8px', 
                              textAlign: 'right',
                              color: aligned ? '#00ff00' : '#ff9900'
                            }}>
                              {aligned ? '✓ ALIGNED' : '⚠ DIVERGE'}
                            </td>
                          </tr>
                        );
                      })
                    ) : (
                      <tr>
                        <td colSpan="5" style={{ padding: '12px', textAlign: 'center', color: '#666' }}>
                          Historical correlation data will appear after the first scrape.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {activeTab === 'Jensen Correlation' && (
            <div style={{ padding: '16px' }}>
              <div style={{ 
                backgroundColor: '#0a0a0a', 
                padding: '16px', 
                border: '1px solid #333',
                marginBottom: '16px'
              }}>
                <h3 style={{ color: '#ff9900', margin: '0 0 12px 0', fontSize: '14px' }}>
                  Correlation Analysis
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
                  <div>
                    <div style={{ color: '#888888', fontSize: '10px' }}>R-Squared</div>
                    <div style={{ color: '#00ff00', fontSize: '24px', fontWeight: 'bold' }}>{data.r_squared || '0.00'}</div>
                  </div>
                  <div>
                    <div style={{ color: '#888888', fontSize: '10px' }}>P-Value</div>
                    <div style={{ color: '#00ff00', fontSize: '24px', fontWeight: 'bold' }}>{data.p_value || '0.000'}</div>
                  </div>
                  <div>
                    <div style={{ color: '#888888', fontSize: '10px' }}>Lead Time</div>
                    <div style={{ color: '#ffcc00', fontSize: '24px', fontWeight: 'bold' }}>{data.lead_time || '3-5d'}</div>
                  </div>
                </div>
              </div>
              
              <div style={{ color: '#ffffff', fontSize: '12px', lineHeight: '1.8' }}>
                <h4 style={{ color: '#ff9900', marginBottom: '8px' }}>Key Insights:</h4>
                <ul style={{ margin: 0, paddingLeft: '20px' }}>
                  {(data.insights || [
                    "Asymmetric zippers correlate with 2.3% higher next-day NVDA returns",
                    "Black leather listings spike 18% in the week before earnings calls",
                    "Schott NYC jackets are the most predictive brand (r=0.74)",
                    "Jensen Score >10 items precede 5%+ NVDA moves 73% of the time"
                  ]).map((insight, i) => (
                    <li key={i} style={{ marginBottom: '8px' }}>
                      {insight}
                    </li>
                  ))}
                </ul>
              </div>
              
              <div style={{ 
                marginTop: '24px', 
                padding: '12px', 
                backgroundColor: '#1a1a00',
                border: '1px solid #666600',
                fontSize: '11px',
                color: '#ffcc00'
              }}>
                ⚠ DISCLAIMER: This is not financial advice. This is fashion advice.
              </div>
            </div>
          )}

          {activeTab === 'Top Listings' && (
            <div style={{ padding: '8px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ backgroundColor: '#1a1a1a' }}>
                    <th style={{ textAlign: 'left', padding: '8px', color: '#888888', fontSize: '11px' }}>Listing</th>
                    <th style={{ textAlign: 'left', padding: '8px', color: '#888888', fontSize: '11px' }}>Designer</th>
                    <th style={{ textAlign: 'right', padding: '8px', color: '#888888', fontSize: '11px' }}>Price</th>
                    <th style={{ textAlign: 'center', padding: '8px', color: '#888888', fontSize: '11px' }}>Jensen Score</th>
                  </tr>
                </thead>
                <tbody>
                  {data.top_listings && data.top_listings.length > 0 ? (
                    data.top_listings.map((listing, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #222' }}>
                        <td style={{ 
                          padding: '8px', 
                          color: listing.jensen_score >= 20 ? '#00ff00' : '#ffffff',
                          fontSize: '11px',
                          maxWidth: '300px',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {listing.title}
                        </td>
                        <td style={{ padding: '8px', color: '#888888', fontSize: '11px' }}>
                          {listing.designer}
                        </td>
                        <td style={{ padding: '8px', color: '#ffffff', fontSize: '11px', textAlign: 'right', fontFamily: 'monospace' }}>
                          ${listing.price.toLocaleString()}
                        </td>
                        <td style={{ padding: '8px', textAlign: 'center' }}>
                          <JensenScoreBadge score={listing.jensen_score} />
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="4" style={{ padding: '24px', textAlign: 'center', color: '#888888' }}>
                        No real listings found in database. Click 'REFRESH LATEST' to scrape.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div style={{ 
          width: '260px',
          borderLeft: '1px solid #333',
          padding: '8px',
          backgroundColor: '#0a0a0a'
        }}>
          <div style={{ marginBottom: '16px' }}>
            <div style={{ color: '#ff9900', fontSize: '12px', fontWeight: 'bold', marginBottom: '4px' }}>
              Grailed Data:
            </div>
            <div style={{ color: '#888888', fontSize: '10px', lineHeight: '1.5' }}>
              Leather jacket resale prices<br />
              Panel: ~150 daily listings<br />
              Categories: Outerwear {'>'} Leather<br />
              Scoring: Jensen-Coded™ Algorithm
            </div>
          </div>
          
          <div style={{ marginBottom: '16px' }}>
            <div style={{ color: '#ff9900', fontSize: '12px', fontWeight: 'bold', marginBottom: '4px' }}>
              NVDA Reference:
            </div>
            <div style={{ color: '#888888', fontSize: '10px', lineHeight: '1.5' }}>
              Yahoo Finance (delayed)<br />
              Ticker: NVDA<br />
              Correlation: β = {data.r_squared ? Math.sqrt(data.r_squared).toFixed(2) : '0.00'}
            </div>
          </div>

          <div style={{ 
            backgroundColor: '#001a00', 
            border: '1px solid #003300',
            padding: '8px',
            marginTop: '16px'
          }}>
            <div style={{ color: '#00ff00', fontSize: '11px', fontWeight: 'bold' }}>
              SIGNAL: BULLISH
            </div>
            <div style={{ color: '#888888', fontSize: '10px', marginTop: '4px' }}>
              Jensen Score trending up.<br />
              Jacket prices leading NVDA.
            </div>
          </div>

          <div style={{ 
            marginTop: '16px',
            padding: '8px',
            border: '1px solid #333'
          }}>
            <div style={{ color: '#888888', fontSize: '10px' }}>
              "The leather jacket market is a leading indicator for semiconductor demand."
            </div>
            <div style={{ color: '#666666', fontSize: '9px', marginTop: '4px', fontStyle: 'italic' }}>
              — No one, ever
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default JensenIndex;
