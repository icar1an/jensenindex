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

  const tabs = ['Inflection', 'Jensen Correlation', 'Top Listings'];
  const timeRanges = ['1W', '1M', '3M', '6M', '1Y', 'Max'];

  // Mock data - in production, fetch from /api/index
  useEffect(() => {
    // Simulate API fetch
    setTimeout(() => {
      setData(getMockData());
      setLoading(false);
    }, 800);
  }, []);

  const getMockData = () => ({
    ticker: "JHLJ",
    name: "Jensen Huang Leather Jacket Index",
    last_updated: "2024-12-28",
    alt_data_metrics: [
      { name: 'Avg Jacket Price', trailing91: 487.32, trailing28: 502.18, trailing7: 518.45, pop91: 5.27, pop28: 3.20, pop7: 2.06, highlighted: true },
      { name: 'Jensen Score (Avg)', trailing91: 6.82, trailing28: 7.14, trailing7: 7.92, pop91: 8.22, pop28: 4.71, pop7: 6.34 },
      { name: 'Daily Listings', trailing91: 147, trailing28: 156, trailing7: 168, pop91: 12.11, pop28: 8.29, pop7: 5.67 },
      { name: 'Items Sold', trailing91: 23, trailing28: 27, trailing7: 31, pop91: 14.50, pop28: 11.11, pop7: 8.89 },
      { name: 'NVDA Correlation (β)', trailing91: 0.73, trailing28: 0.68, trailing7: 0.81, pop91: 2.34, pop28: 5.12, pop7: 8.94 },
      { name: 'Price/NVDA Ratio', trailing91: 3.52, trailing28: 3.61, trailing7: 3.74, pop91: -1.12, pop28: 2.49, pop7: 3.60 },
    ],
    weekly_data: [
      { week: '15-Nov', jacket: 3.49, nvda: 4.40, jensen: 6.2 },
      { week: '22-Nov', jacket: -1.23, nvda: -0.85, jensen: 5.8 },
      { week: '29-Nov', jacket: 2.87, nvda: 3.22, jensen: 7.1 },
      { week: '06-Dec', jacket: 5.12, nvda: 6.85, jensen: 8.4 },
      { week: '13-Dec', jacket: -0.45, nvda: -1.17, jensen: 6.9 },
      { week: '20-Dec', jacket: 4.33, nvda: 5.21, jensen: 7.8 },
      { week: '27-Dec', jacket: 2.18, nvda: 2.74, jensen: 7.2 },
    ],
    top_listings: [
      { id: '12998877', title: 'Black Leather Tech CEO Biker (NVIDIA investor energy)', designer: 'Unknown', price: 320, jensen_score: 25 },
      { id: '12847291', title: 'Schott NYC 626 Leather Moto Jacket Black', designer: 'Schott NYC', price: 650, jensen_score: 12 },
      { id: '12903847', title: 'AllSaints Cargo Leather Biker Jacket', designer: 'AllSaints', price: 380, jensen_score: 10 },
      { id: '12756392', title: 'The Kooples Asymmetric Leather Jacket', designer: 'The Kooples', price: 425, jensen_score: 9 },
      { id: '12901234', title: 'Saint Laurent L01 Classic Motorcycle', designer: 'Saint Laurent', price: 2400, jensen_score: 8 },
      { id: '12776543', title: 'Vintage Cafe Racer Black Leather', designer: 'Vintage', price: 245, jensen_score: 8 },
    ],
  });

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
          marginRight: '16px'
        }}>
          ▲ 2.18%
        </span>
        <span style={{ 
          color: '#888888', 
          fontSize: '11px',
          marginRight: '16px'
        }}>
          NVDA: $142.87 ▲ 2.74%
        </span>
        <button style={{
          backgroundColor: '#ff6600',
          color: 'white',
          border: 'none',
          padding: '2px 12px',
          fontSize: '11px',
          cursor: 'pointer',
          marginLeft: 'auto',
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
            Data up to {data.last_updated}
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
                  {data.alt_data_metrics.map((metric, idx) => (
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
                  ))}
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
                    {data.weekly_data.map((row, idx) => {
                      const jacketNum = parseFloat(row.jacket);
                      const nvdaNum = parseFloat(row.nvda);
                      const aligned = (jacketNum > 0 && nvdaNum > 0) || (jacketNum < 0 && nvdaNum < 0);
                      
                      return (
                        <tr key={idx} style={{ borderBottom: '1px solid #222' }}>
                          <td style={{ color: '#ffffff', padding: '3px 8px' }}>{row.week}</td>
                          <ValueCell value={row.jacket} highlight={row.jacket > 4 ? 'yellow' : null} />
                          <ValueCell value={row.nvda} />
                          <td style={{ color: row.jensen > 7 ? '#00ff00' : '#ffffff', padding: '3px 8px', textAlign: 'right' }}>
                            {row.jensen.toFixed(1)}
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
                    })}
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
                    <div style={{ color: '#00ff00', fontSize: '24px', fontWeight: 'bold' }}>0.67</div>
                  </div>
                  <div>
                    <div style={{ color: '#888888', fontSize: '10px' }}>P-Value</div>
                    <div style={{ color: '#00ff00', fontSize: '24px', fontWeight: 'bold' }}>0.003</div>
                  </div>
                  <div>
                    <div style={{ color: '#888888', fontSize: '10px' }}>Lead Time</div>
                    <div style={{ color: '#ffcc00', fontSize: '24px', fontWeight: 'bold' }}>3-5d</div>
                  </div>
                </div>
              </div>
              
              <div style={{ color: '#ffffff', fontSize: '12px', lineHeight: '1.8' }}>
                <h4 style={{ color: '#ff9900', marginBottom: '8px' }}>Key Insights:</h4>
                <ul style={{ margin: 0, paddingLeft: '20px' }}>
                  <li style={{ marginBottom: '8px' }}>
                    <span style={{ color: '#00ff00' }}>Asymmetric zippers</span> correlate with 2.3% higher next-day NVDA returns
                  </li>
                  <li style={{ marginBottom: '8px' }}>
                    Black leather listings spike <span style={{ color: '#ffcc00' }}>18%</span> in the week before earnings calls
                  </li>
                  <li style={{ marginBottom: '8px' }}>
                    <span style={{ color: '#00ff00' }}>Schott NYC</span> jackets are the most predictive brand (r=0.74)
                  </li>
                  <li style={{ marginBottom: '8px' }}>
                    Jensen Score {'>'}10 items precede 5%+ NVDA moves <span style={{ color: '#00ff00' }}>73%</span> of the time
                  </li>
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
                  {data.top_listings.map((listing, idx) => (
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
                  ))}
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
              Correlation: β = 0.73
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
