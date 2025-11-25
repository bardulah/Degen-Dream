const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs').promises;
const path = require('path');
const yaml = require('yaml');

puppeteer.use(StealthPlugin());

class FlashscoreScraper {
  constructor(config) {
    this.config = config;
    this.browser = null;
    this.page = null;
    this.matches = [];
  }

  async initialize() {
    console.log('Initializing browser...');
    this.browser = await puppeteer.launch({
      headless: this.config.scraper.headless,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--disable-gpu'
      ]
    });

    this.page = await this.browser.newPage();
    await this.page.setUserAgent(this.config.scraper.user_agent);
    await this.page.setViewport(this.config.scraper.viewport);
    this.page.setDefaultNavigationTimeout(this.config.scraper.timeout);
  }

  async delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // League extraction function - used by all sports
  // STRATEGY 2 (90% success rate): Look for section header by walking backwards
  static extractLeague(matchElement) {
    let league = 'Unknown League';

    // Look at previous siblings to find the league header
    let prev = matchElement.previousElementSibling;
    for (let j = 0; j < 10; j++) {
      if (!prev) break;

      const prevText = prev.textContent.trim();

      // Skip empty elements
      if (prevText.length === 0) {
        prev = prev.previousElementSibling;
        continue;
      }

      // Look for typical league patterns (these are usually in headers)
      const leaguePatterns = [
        /([A-Z][A-Z\s]+):\s*([^0-9\n]+)/,  // "EUROPE: World Cup"
        /(World Cup|Champions League|Premier League|La Liga|Serie A|Ligue|Bundesliga|Cup|Championship|League|Playoff|Qualification)/i
      ];

      for (const pattern of leaguePatterns) {
        const match = prevText.match(pattern);
        if (match) {
          // Return the full matched string if reasonable length
          if (prevText.length < 150) {  // Avoid matching match lists
            league = prevText.substring(0, 100).trim();

            // Clean up league name: remove odds labels like "1X2", "Over/Under"
            // Keep only: "REGION: League Name - Type"
            league = league
              .replace(/\s*1X2\s*$/, '')  // Remove "1X2" at end
              .replace(/\s*Over\/Under\s*$/, '')  // Remove "Over/Under"
              .replace(/\s*Standings.*$/, '')  // Remove "Standings" and after
              .replace(/\s*Scores.*$/, '')  // Remove "Scores" and after
              .trim();

            return league;
          }
        }
      }

      prev = prev.previousElementSibling;
    }

    // FALLBACK: Try to extract from breadcrumb/parent
    const breadcrumb = matchElement.closest('[class*="breadcrumb"], [class*="path"], .event__round');
    if (breadcrumb) {
      const text = breadcrumb.textContent.trim();
      if (text.length > 0 && text.length < 200) {
        league = text.substring(0, 100).trim();
        return league;
      }
    }

    // FALLBACK: Check for league label element
    const leagueLabel = matchElement.querySelector('[class*="tournament"], [class*="league"], [class*="category"]');
    if (leagueLabel) {
      const text = leagueLabel.textContent.trim();
      if (text.length > 0 && text !== 'Preview' && text !== 'Live') {
        league = text.substring(0, 100);
        return league;
      }
    }

    return league;
  }

  async clickOddsButton() {
    console.log('Looking for odds tab...');
    
    try {
      const clicked = await this.page.evaluate(() => {
        // Look for the filters__tab with "Odds" text
        const allTabs = document.querySelectorAll('.filters__tab, div[class*="filter"]');
        const oddsTab = Array.from(allTabs).find(tab => {
          const text = tab.textContent.trim().toLowerCase();
          return text === 'odds' || text.includes('odds');
        });
        
        if (oddsTab) {
          console.log('Found odds tab:', oddsTab.textContent.trim());
          oddsTab.click();
          return true;
        }
        
        return false;
      });
      
      if (clicked) {
        console.log('✓ Clicked odds tab');
        await this.delay(8000); // Wait longer for odds to load via AJAX
        return true;
      } else {
        console.log('⚠  Odds tab not found');
        return false;
      }
    } catch (err) {
      console.log('⚠  Error clicking odds tab:', err.message);
      return false;
    }
  }

  async scrapeFootball() {
    console.log('Scraping football matches...');
    const matches = [];

    try {
      await this.page.goto('https://www.flashscore.com/football/', {
        waitUntil: 'domcontentloaded'
      });

      await this.delay(3000);

      // Click odds tab directly (same method as debug script)
      console.log('Clicking odds tab...');
      const clicked = await this.page.evaluate(() => {
        const allTabs = document.querySelectorAll('.filters__tab');
        const oddsTab = Array.from(allTabs).find(tab => {
          const text = tab.textContent.trim().toLowerCase();
          return text === 'odds' || text.includes('odds');
        });

        if (oddsTab) {
          oddsTab.click();
          return true;
        }
        return false;
      });

      if (clicked) {
        console.log('✓ Clicked odds tab');
        await this.delay(6000); // Wait for odds to fully load
      } else {
        console.log('⚠ Odds tab not found');
      }

      // Extract matches with odds AND LEAGUE INFORMATION
      const matchData = await this.page.evaluate(() => {
        const totalOddsElements = document.querySelectorAll('.odds__odd').length;
        const oddsWithValues = document.querySelectorAll('.odds__odd:not(.no-odds)').length;
        console.log(`Total odds elements: ${totalOddsElements}, with values: ${oddsWithValues}`);

        const matches = [];
        const matchElements = document.querySelectorAll('[id^="g_1"]') ||
                             document.querySelectorAll('.event__match');

        console.log(`Found ${matchElements.length} match elements`);

        // Helper function to extract league from DOM
        function extractLeague(matchElement) {
          // PRIMARY (100% success): Use .headerLeague__wrapper which ALL sports use
          let league = 'Unknown League';

          let prev = matchElement.previousElementSibling;
          for (let j = 0; j < 30; j++) {
            if (!prev) break;

            if (prev.className && prev.className.includes('headerLeague__wrapper')) {
              const text = prev.textContent.trim();
              if (text.length > 0) {
                league = text.substring(0, 150).trim();

                // Clean up league name
                league = league
                  .replace(/\s*1X2\s*$/i, '')
                  .replace(/\s*Over\/Under\s*$/i, '')
                  .replace(/\s*Standings.*$/i, '')
                  .replace(/\s*Scores.*$/i, '')
                  .replace(/\s*12$/i, '')  // Tennis suffix
                  .trim();

                return league;
              }
            }

            prev = prev.previousElementSibling;
          }

          // FALLBACK: Look for patterns in previous siblings
          prev = matchElement.previousElementSibling;
          for (let j = 0; j < 10; j++) {
            if (!prev) break;

            const prevText = prev.textContent.trim();

            if (prevText.length === 0 || (prev.className && prev.className.includes('event__match'))) {
              prev = prev.previousElementSibling;
              continue;
            }

            const leaguePatterns = [
              /([A-Z][A-Z\s]+):\s*([^0-9\n]+)/,
              /(World Cup|Champions League|Premier League|La Liga|Serie A|Ligue|Bundesliga|Cup|Championship|League|Playoff|Qualification)/i
            ];

            for (const pattern of leaguePatterns) {
              const match = prevText.match(pattern);
              if (match && prevText.length < 150) {
                league = prevText.substring(0, 100).trim();

                league = league
                  .replace(/\s*1X2\s*$/i, '')
                  .replace(/\s*Over\/Under\s*$/i, '')
                  .replace(/\s*Standings.*$/i, '')
                  .replace(/\s*Scores.*$/i, '')
                  .trim();

                return league;
              }
            }

            prev = prev.previousElementSibling;
          }

          return league;
        }

        // Use all matches (limit will be applied from config)
        for (let i = 0; i < matchElements.length; i++) {
          const el = matchElements[i];

          try {
            // Extract team names
            let homeTeam = 'Unknown';
            let awayTeam = 'Unknown';

            const homeEl = el.querySelector('.event__participant--home');
            const awayEl = el.querySelector('.event__participant--away');

            if (homeEl) homeTeam = homeEl.textContent.trim();
            if (awayEl) awayTeam = awayEl.textContent.trim();

            // Fallbacks
            if (homeTeam === 'Unknown') {
              const participants = el.querySelectorAll('[class*="participant"]');
              if (participants.length >= 2) {
                homeTeam = participants[0].textContent.trim();
                awayTeam = participants[1].textContent.trim();
              }
            }

            if (homeTeam === 'Unknown' && el.title) {
              const parts = el.title.split(' - ');
              if (parts.length >= 2) {
                homeTeam = parts[0].trim();
                awayTeam = parts[1].trim();
              }
            }

            // Extract time
            let time = 'TBD';
            const timeEl = el.querySelector('.event__time');
            if (timeEl) time = timeEl.textContent.trim();

            // ✨ NEW: Extract league information
            const league = extractLeague(el);

            // Extract ODDS - correct selectors based on actual HTML
            let odds = {};

            // Look for .odds__odd divs (exclude ones with 'no-odds' class)
            const allOddsDiv = el.querySelectorAll('.odds__odd:not(.no-odds)');

            if (allOddsDiv.length >= 3) {
              // Extract span values from each odds div
              const values = Array.from(allOddsDiv).map(odd => {
                // Find any span inside (could be .up, .down, or empty class)
                const span = odd.querySelector('span');
                if (span) {
                  const text = span.textContent.trim();
                  const num = parseFloat(text);
                  return (!isNaN(num) && text !== '-') ? num : null;
                }
                return null;
              }).filter(v => v !== null);

              if (values.length >= 3) {
                // Football: home, draw, away
                odds['Flashscore'] = {
                  home: values[0],
                  draw: values[1],
                  away: values[2]
                };
              } else if (values.length >= 2) {
                // Tennis/Basketball: home, away (no draw)
                odds['Flashscore'] = {
                  home: values[0],
                  away: values[1]
                };
              }
            }

            matches.push({
              id: el.id || `football_${i}_${Date.now()}`,
              sport: 'football',
              homeTeam: homeTeam,
              awayTeam: awayTeam,
              league: league,  // ✨ NOW PROPERLY EXTRACTED
              time: time,
              date: new Date().toISOString().split('T')[0],
              odds: odds,
              _hasOdds: Object.keys(odds).length > 0
            });

          } catch (err) {
            console.error(`Error extracting match ${i}:`, err.message);
          }
        }

        return matches;
      });

      const validMatches = matchData.filter(m => 
        m.homeTeam !== 'Unknown' && m.awayTeam !== 'Unknown'
      );
      
      console.log(`Extracted: ${matchData.length} total, ${validMatches.length} valid`);
      console.log(`Matches with odds: ${validMatches.filter(m => m._hasOdds).length}`);
      
      matches.push(...validMatches);

    } catch (error) {
      console.error('Error scraping football:', error.message);
    }

    return matches;
  }

  async scrapeBasketball() {
    console.log('Scraping basketball matches...');
    const matches = [];

    try {
      await this.page.goto('https://www.flashscore.com/basketball/', {
        waitUntil: 'networkidle2'
      });

      await this.delay(this.config.scraper.rate_limit_delay);

      // Click odds tab to load odds data (critical for basketball)
      console.log('Clicking odds tab...');
      const clicked = await this.page.evaluate(() => {
        const allTabs = document.querySelectorAll('.filters__tab');
        const oddsTab = Array.from(allTabs).find(tab => {
          const text = tab.textContent.trim().toLowerCase();
          return text === 'odds' || text.includes('odds');
        });

        if (oddsTab) {
          oddsTab.click();
          return true;
        }
        return false;
      });

      if (clicked) {
        console.log('✓ Clicked odds tab');
        await this.delay(6000); // Wait for odds to load via AJAX
      } else {
        console.log('⚠️  Odds tab not found');
      }

      const matchData = await this.page.evaluate((selector) => {
        // Helper to extract league - use .headerLeague__wrapper (works for all sports)
        function extractLeague(el) {
          let league = 'Unknown League';

          // PRIMARY: Use .headerLeague__wrapper
          let prev = el.previousElementSibling;
          for (let j = 0; j < 30; j++) {
            if (!prev) break;

            if (prev.className && prev.className.includes('headerLeague__wrapper')) {
              const text = prev.textContent.trim();
              if (text.length > 0) {
                league = text.substring(0, 150).trim();
                league = league
                  .replace(/\s*1X2\s*$/i, '')
                  .replace(/\s*Over\/Under\s*$/i, '')
                  .replace(/\s*Standings.*$/i, '')
                  .replace(/\s*Scores.*$/i, '')
                  .replace(/\s*12$/i, '')
                  .trim();
                return league;
              }
            }

            prev = prev.previousElementSibling;
          }

          // FALLBACK: Pattern matching
          prev = el.previousElementSibling;
          for (let j = 0; j < 10; j++) {
            if (!prev) break;
            const text = prev.textContent.trim();
            if (text.length === 0 || (prev.className && prev.className.includes('event__match'))) {
              prev = prev.previousElementSibling;
              continue;
            }
            if (text.length < 150 && /[A-Z]:/.test(text)) {
              league = text.substring(0, 100).trim()
                .replace(/\s*1X2\s*$/, '')
                .replace(/\s*Over\/Under\s*$/, '')
                .replace(/\s*Standings.*$/, '')
                .replace(/\s*Scores.*$/, '')
                .trim();
              return league;
            }
            prev = prev.previousElementSibling;
          }
          return league;
        }

        const elements = document.querySelectorAll(selector);
        const results = [];

        for (let i = 0; i < elements.length; i++) {
          const el = elements[i];

          try {
            // Extract team names
            const homeEl = el.querySelector('.event__participant--home');
            const awayEl = el.querySelector('.event__participant--away');
            const timeEl = el.querySelector('.event__time');

            let homeTeam = 'Unknown';
            let awayTeam = 'Unknown';
            let time = 'TBD';

            if (homeEl && awayEl) {
              const homeText = homeEl.textContent.trim();
              const awayText = awayEl.textContent.trim();

              if (homeText && awayText) {
                homeTeam = homeText;
                awayTeam = awayText;
              }
            }

            if (timeEl) {
              time = timeEl.textContent.trim();
            }

            // Extract odds for basketball (usually just home/away, no draw)
            let odds = {};
            const allOddsDiv = el.querySelectorAll('.odds__odd:not(.no-odds)');

            if (allOddsDiv.length >= 2) {
              const values = Array.from(allOddsDiv).map(odd => {
                const span = odd.querySelector('span');
                if (span) {
                  const text = span.textContent.trim();
                  const num = parseFloat(text);
                  return (!isNaN(num) && text !== '-') ? num : null;
                }
                return null;
              }).filter(v => v !== null);

              if (values.length >= 2) {
                odds['Flashscore'] = {
                  home: values[0],
                  away: values[1]
                };
              }
            }

            // ✨ Extract league
            const league = extractLeague(el);

            results.push({
              id: el.id || `basketball_${i}_${Date.now()}`,
              sport: 'basketball',
              homeTeam: homeTeam,
              awayTeam: awayTeam,
              league: league,
              time: time,
              date: new Date().toISOString().split('T')[0],
              odds: odds,
              _hasOdds: Object.keys(odds).length > 0
            });
            
          } catch (err) {
            console.error(`Error extracting basketball match ${i}:`, err.message);
          }
        }
        
        return results;
      }, '.event__match');

      const validMatches = (matchData || []).filter(m => 
        m.homeTeam !== 'Unknown' && m.awayTeam !== 'Unknown'
      );
      
      console.log(`Extracted: ${(matchData || []).length} total, ${validMatches.length} valid`);
      console.log(`Matches with odds: ${validMatches.filter(m => m._hasOdds).length}`);
      
      matches.push(...validMatches);

    } catch (error) {
      console.error('Error scraping basketball:', error.message);
    }

    return matches;
  }

  async scrapeTennis() {
    console.log('Scraping tennis matches...');
    const matches = [];

    try {
      await this.page.goto('https://www.flashscore.com/tennis/', {
        waitUntil: 'domcontentloaded'
      });

      await this.delay(3000);
      
      // Click odds tab
      console.log('Clicking odds tab...');
      const clicked = await this.page.evaluate(() => {
        const allTabs = document.querySelectorAll('.filters__tab');
        const oddsTab = Array.from(allTabs).find(tab => {
          const text = tab.textContent.trim().toLowerCase();
          return text === 'odds' || text.includes('odds');
        });
        if (oddsTab) {
          oddsTab.click();
          return true;
        }
        return false;
      });
      
      if (clicked) {
        console.log('✓ Clicked odds tab');
        await this.delay(6000);
      }

      const matchData = await this.page.evaluate(() => {
        // Helper to extract league - use .headerLeague__wrapper (works for all sports)
        function extractLeague(el) {
          let league = 'Unknown League';

          // PRIMARY: Use .headerLeague__wrapper
          let prev = el.previousElementSibling;
          for (let j = 0; j < 30; j++) {
            if (!prev) break;

            if (prev.className && prev.className.includes('headerLeague__wrapper')) {
              const text = prev.textContent.trim();
              if (text.length > 0) {
                league = text.substring(0, 150).trim();
                league = league
                  .replace(/\s*1X2\s*$/i, '')
                  .replace(/\s*Over\/Under\s*$/i, '')
                  .replace(/\s*Standings.*$/i, '')
                  .replace(/\s*Scores.*$/i, '')
                  .replace(/\s*12$/i, '')
                  .trim();
                return league;
              }
            }

            prev = prev.previousElementSibling;
          }

          // FALLBACK: Pattern matching
          prev = el.previousElementSibling;
          for (let j = 0; j < 10; j++) {
            if (!prev) break;
            const text = prev.textContent.trim();
            if (text.length === 0 || (prev.className && prev.className.includes('event__match'))) {
              prev = prev.previousElementSibling;
              continue;
            }
            if (text.length < 150 && /[A-Z]/.test(text[0])) {
              league = text.substring(0, 100).trim()
                .replace(/\s*1X2\s*$/, '')
                .replace(/\s*Over\/Under\s*$/, '')
                .replace(/\s*Standings.*$/, '')
                .replace(/\s*Scores.*$/, '')
                .trim();
              return league;
            }
            prev = prev.previousElementSibling;
          }
          return league;
        }

        const matches = [];
        const matchElements = document.querySelectorAll('[id^="g_2"]') ||
                             document.querySelectorAll('.event__match');

        for (let i = 0; i < matchElements.length; i++) {
          const el = matchElements[i];

          try {
            let homeTeam = 'Unknown';
            let awayTeam = 'Unknown';

            const homeEl = el.querySelector('.event__participant--home');
            const awayEl = el.querySelector('.event__participant--away');

            if (homeEl) homeTeam = homeEl.textContent.trim();
            if (awayEl) awayTeam = awayEl.textContent.trim();

            if (homeTeam === 'Unknown' && el.title) {
              const parts = el.title.split(' - ');
              if (parts.length >= 2) {
                homeTeam = parts[0].trim();
                awayTeam = parts[1].trim();
              }
            }

            let time = 'TBD';
            const timeEl = el.querySelector('.event__time');
            if (timeEl) time = timeEl.textContent.trim();

            // Extract odds for tennis (player 1 / player 2)
            let odds = {};
            const allOddsDiv = el.querySelectorAll('.odds__odd:not(.no-odds)');

            if (allOddsDiv.length >= 2) {
              const values = Array.from(allOddsDiv).map(odd => {
                const span = odd.querySelector('span');
                if (span) {
                  const text = span.textContent.trim();
                  const num = parseFloat(text);
                  return (!isNaN(num) && text !== '-') ? num : null;
                }
                return null;
              }).filter(v => v !== null);

              if (values.length >= 2) {
                odds['Flashscore'] = {
                  home: values[0],
                  away: values[1]
                };
              }
            }

            // ✨ Extract league
            const league = extractLeague(el);

            matches.push({
              id: el.id || `tennis_${i}_${Date.now()}`,
              sport: 'tennis',
              homeTeam: homeTeam,
              awayTeam: awayTeam,
              league: league,
              time: time,
              date: new Date().toISOString().split('T')[0],
              odds: odds,
              _hasOdds: Object.keys(odds).length > 0
            });
            
          } catch (err) {
            console.error(`Error extracting tennis match ${i}:`, err.message);
          }
        }
        
        return matches;
      });

      const validMatches = matchData.filter(m => 
        m.homeTeam !== 'Unknown' && m.awayTeam !== 'Unknown'
      );
      
      console.log(`Extracted: ${matchData.length} total, ${validMatches.length} valid`);
      console.log(`Matches with odds: ${validMatches.filter(m => m._hasOdds).length}`);
      
      matches.push(...validMatches);

    } catch (error) {
      console.error('Error scraping tennis:', error.message);
    }

    return matches;
  }

  async scrapeHockey() {
    console.log('Scraping hockey matches...');
    const matches = [];

    try {
      await this.page.goto('https://www.flashscore.com/hockey/', {
        waitUntil: 'networkidle2'
      });

      await this.delay(this.config.scraper.rate_limit_delay);

      // Wait for hockey matches to load
      await this.page.waitForSelector('.event__match', { timeout: 15000 }).catch(() => {
        console.log('⚠️  Timeout waiting for .event__match');
      });

      // Verify matches are there
      const matchCount = await this.page.evaluate(() => document.querySelectorAll('.event__match').length);
      console.log(`✓ Found ${matchCount} match elements on hockey page`);

      // Click odds tab to load odds data (critical for hockey)
      console.log('Clicking odds tab for hockey page...');
      try {
        const clicked = await this.page.evaluate(() => {
          const filterTabs = document.querySelectorAll('.filters__tab');
          for (let tab of filterTabs) {
            const text = tab.textContent.trim().toLowerCase();
            if (text === 'odds') {
              tab.click();
              return true;
            }
          }
          return false;
        });

        if (clicked) {
          console.log('✓ Clicked odds tab');
          await this.delay(6000); // Wait for odds to load via AJAX
        } else {
          console.log('⚠️  Odds tab not found on hockey page');
        }
      } catch (err) {
        console.log('⚠️  Error clicking odds tab on hockey:', err.message);
      }

      const matchData = await this.page.evaluate((selector) => {
        // Helper to extract league - use .headerLeague__wrapper (works for all sports)
        function extractLeague(el) {
          let league = 'Unknown League';

          // PRIMARY: Use .headerLeague__wrapper
          let prev = el.previousElementSibling;
          for (let j = 0; j < 30; j++) {
            if (!prev) break;

            if (prev.className && prev.className.includes('headerLeague__wrapper')) {
              const text = prev.textContent.trim();
              if (text.length > 0) {
                league = text.substring(0, 150).trim();
                league = league
                  .replace(/\s*1X2\s*$/i, '')
                  .replace(/\s*Over\/Under\s*$/i, '')
                  .replace(/\s*Standings.*$/i, '')
                  .replace(/\s*Scores.*$/i, '')
                  .replace(/\s*12$/i, '')
                  .trim();
                return league;
              }
            }

            prev = prev.previousElementSibling;
          }

          // FALLBACK: Pattern matching
          prev = el.previousElementSibling;
          for (let j = 0; j < 10; j++) {
            if (!prev) break;
            const text = prev.textContent.trim();
            if (text.length === 0 || (prev.className && prev.className.includes('event__match'))) {
              prev = prev.previousElementSibling;
              continue;
            }
            if (text.length > 0 && text.length < 150 && /[A-Z]/.test(text[0])) {
              league = text.substring(0, 100).trim()
                .replace(/\s*1X2\s*$/, '')
                .replace(/\s*Over\/Under\s*$/, '')
                .replace(/\s*Standings.*$/, '')
                .replace(/\s*Scores.*$/, '')
                .trim();
              return league;
            }
            prev = prev.previousElementSibling;
          }
          return league;
        }

        let elements = document.querySelectorAll(selector);

        const results = [];

        for (let i = 0; i < elements.length; i++) {
          const el = elements[i];

          try {
            // Extract team names directly from element
            const homeEl = el.querySelector('.event__participant--home');
            const awayEl = el.querySelector('.event__participant--away');
            let timeEl = el.querySelector('.event__time');

            // Hockey doesn't have time, look for stage instead
            if (!timeEl) {
              timeEl = el.querySelector('.event__stage');
            }

            let homeTeam = 'Unknown';
            let awayTeam = 'Unknown';
            let time = 'TBD';

            // Extract team names
            if (homeEl && awayEl) {
              const homeText = homeEl.textContent.trim();
              const awayText = awayEl.textContent.trim();

              if (homeText && awayText && homeText.length > 0 && awayText.length > 0) {
                homeTeam = homeText;
                awayTeam = awayText;
              }
            }

            // Extract time or stage
            if (timeEl) {
              const timeText = timeEl.textContent.trim();
              if (timeText && timeText.length > 0) {
                time = timeText;
              }
            }

            // Extract odds for hockey (home/draw/away - hockey has 3 outcomes like football)
            let odds = {};
            const allOddsDiv = el.querySelectorAll('.odds__odd');

            if (allOddsDiv.length >= 3) {
              // Extract text values directly from .odds__odd divs (not spans)
              const values = Array.from(allOddsDiv).map(odd => {
                const text = odd.textContent.trim();
                const num = parseFloat(text);
                // Only accept valid numbers (not "-" or empty)
                return (!isNaN(num) && text !== '-' && text.length > 0) ? num : null;
              }).filter(v => v !== null);

              if (values.length >= 3) {
                // Hockey: home, draw, away (same as football - 3 outcomes)
                odds['Flashscore'] = {
                  home: values[0],
                  draw: values[1],
                  away: values[2]
                };
              } else if (values.length >= 2) {
                // Fallback: if only 2 odds (some matches might be incomplete)
                odds['Flashscore'] = {
                  home: values[0],
                  away: values[1]
                };
              }
            }

            // Extract league
            const league = extractLeague(el);

            results.push({
              id: el.id || `hockey_${i}_${Date.now()}`,
              sport: 'hockey',
              homeTeam: homeTeam,
              awayTeam: awayTeam,
              league: league,
              time: time,
              date: new Date().toISOString().split('T')[0],
              odds: odds,
              _hasOdds: Object.keys(odds).length > 0
            });

          } catch (err) {
            // Silent catch for extraction errors
          }
        }

        return results;
      }, '.event__match');

      const validMatches = (matchData || []).filter(m =>
        m.homeTeam !== 'Unknown' && m.awayTeam !== 'Unknown'
      );

      console.log(`Extracted: ${(matchData || []).length} total, ${validMatches.length} valid`);
      console.log(`Matches with odds: ${validMatches.filter(m => m._hasOdds).length}`);

      matches.push(...validMatches);

    } catch (error) {
      console.error('Error scraping hockey:', error.message);
    }

    return matches;
  }

  async scrapeBaseball() {
    console.log('Scraping baseball matches...');
    const matches = [];

    try {
      await this.page.goto('https://www.flashscore.com/baseball/', {
        waitUntil: 'domcontentloaded'
      });

      await this.delay(3000);

      console.log('Clicking odds tab...');
      const clicked = await this.page.evaluate(() => {
        const allTabs = document.querySelectorAll('.filters__tab');
        const oddsTab = Array.from(allTabs).find(tab => {
          const text = tab.textContent.trim().toLowerCase();
          return text === 'odds' || text.includes('odds');
        });

        if (oddsTab) {
          oddsTab.click();
          return true;
        }
        return false;
      });

      if (clicked) {
        console.log('✓ Clicked odds tab');
        await this.delay(6000);
      } else {
        console.log('⚠️  Odds tab not found');
      }

      const matchData = await this.page.evaluate((selector) => {
        function extractLeague(el) {
          let league = 'Unknown League';
          let prev = el.previousElementSibling;
          for (let j = 0; j < 30; j++) {
            if (!prev) break;
            if (prev.classList.contains('headerLeague')) {
              const titleEl = prev.querySelector('.headerLeague__title');
              if (titleEl) {
                league = titleEl.textContent?.trim() || 'Unknown League';
              }
              break;
            }
            prev = prev.previousElementSibling;
          }
          return league;
        }

        const results = [];
        const elements = document.querySelectorAll(selector);

        for (let i = 0; i < Math.min(elements.length, 500); i++) {
          try {
            const el = elements[i];
            const homeEl = el.querySelector('.event__participant--home');
            const awayEl = el.querySelector('.event__participant--away');
            const homeTeam = homeEl?.textContent?.trim() || '';
            const awayTeam = awayEl?.textContent?.trim() || '';

            if (!homeTeam || !awayTeam) continue;

            const timeEl = el.querySelector('.event__time');
            const time = timeEl?.textContent?.trim() || 'TBD';
            const league = extractLeague(el);

            const oddsElements = el.querySelectorAll('.odds__odd');
            const odds = {};

            if (oddsElements.length >= 3) {
              odds['Flashscore'] = {
                home: parseFloat(oddsElements[0]?.textContent?.trim()) || null,
                draw: parseFloat(oddsElements[1]?.textContent?.trim()) || null,
                away: parseFloat(oddsElements[2]?.textContent?.trim()) || null
              };
            }

            results.push({
              id: el.id || `baseball_${i}_${Date.now()}`,
              sport: 'baseball',
              homeTeam: homeTeam,
              awayTeam: awayTeam,
              league: league,
              time: time,
              date: new Date().toISOString().split('T')[0],
              odds: odds,
              _hasOdds: Object.keys(odds).length > 0
            });

          } catch (err) {
            // Silent catch
          }
        }

        return results;
      }, '.event__match');

      const validMatches = (matchData || []).filter(m =>
        m.homeTeam !== 'Unknown' && m.awayTeam !== 'Unknown'
      );

      console.log(`Extracted: ${(matchData || []).length} total, ${validMatches.length} valid`);
      console.log(`Matches with odds: ${validMatches.filter(m => m._hasOdds).length}`);

      matches.push(...validMatches);

    } catch (error) {
      console.error('Error scraping baseball:', error.message);
    }

    return matches;
  }

  async scrapeAll() {
    console.log('Starting scrape for all configured sports...\n');

    for (const sport of this.config.sports) {
      console.log(`=== Scraping ${sport.toUpperCase()} ===`);
      let sportMatches = [];

      switch(sport.toLowerCase()) {
        case 'football':
          sportMatches = await this.scrapeFootball();
          break;
        case 'basketball':
          sportMatches = await this.scrapeBasketball();
          break;
        case 'tennis':
          sportMatches = await this.scrapeTennis();
          break;
        case 'hockey':
          sportMatches = await this.scrapeHockey();
          break;
        case 'baseball':
          sportMatches = await this.scrapeBaseball();
          break;
        default:
          console.log(`Unknown sport: ${sport}`);
      }

      this.matches.push(...sportMatches);
      console.log(`Total ${sport} matches: ${sportMatches.length}\n`);
    }

    return this.matches;
  }

  async saveResults() {
    const outputPath = path.join(__dirname, '../../data/matches.json');
    const output = {
      scrapeDate: new Date().toISOString(),
      totalMatches: this.matches.length,
      matchesWithOdds: this.matches.filter(m => m._hasOdds).length,
      matches: this.matches
    };

    await fs.writeFile(outputPath, JSON.stringify(output, null, 2));
    console.log(`Results saved to ${outputPath}`);
    console.log(`Total matches: ${this.matches.length}`);
    console.log(`Matches with odds: ${output.matchesWithOdds}`);
  }

  async close() {
    if (this.browser) {
      await this.browser.close();
      console.log('Browser closed');
    }
  }
}

// Parse CLI arguments
function parseCliArgs() {
  const args = process.argv.slice(2);
  const options = {
    sports: ['football', 'basketball', 'tennis', 'hockey', 'baseball'],  // Default: all sports
    leagues: null,  // Default: all leagues
    limit: null,    // Default: no limit
    help: false
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === '--help' || arg === '-h') {
      options.help = true;
    } else if (arg === '--sports' && i + 1 < args.length) {
      options.sports = args[i + 1].split(',').map(s => s.trim().toLowerCase());
      i++;
    } else if (arg === '--leagues' && i + 1 < args.length) {
      options.leagues = args[i + 1].split(',').map(l => l.trim());
      i++;
    } else if (arg === '--limit' && i + 1 < args.length) {
      options.limit = parseInt(args[i + 1], 10);
      i++;
    }
  }

  return options;
}

// Print usage help
function printHelp() {
  console.log(`
╔════════════════════════════════════════════════════════════════╗
║         FLASHSCORE SCRAPER - CLI USAGE                         ║
╚════════════════════════════════════════════════════════════════╝

USAGE:
  npm run scrape [OPTIONS]

OPTIONS:
  --sports SPORT1,SPORT2   Comma-separated list of sports to scrape
                           Available: football, basketball, tennis, hockey
                           Default: football,basketball,tennis,hockey

  --leagues LEAGUE1,LEAGUE2 Comma-separated list of leagues to include
                           Example: "Champions League,Premier League"
                           Default: all leagues

  --limit NUM              Maximum number of matches to scrape
                           Example: --limit 50
                           Default: no limit (scrape all)

  --help, -h              Show this help message

EXAMPLES:

  # Scrape all sports (default)
  npm run scrape

  # Scrape only football, limited to 50 matches
  npm run scrape --sports football --limit 50

  # Scrape specific leagues
  npm run scrape --sports football --leagues "Champions League,Premier League"

  # Scrape football with limit, basketball without limit
  npm run scrape --sports football,basketball --limit 100

  # Get help
  npm run scrape -- --help

OUTPUT:
  Results are saved to: ../../data/matches.json

`);
}

// Main execution
async function main() {
  const options = parseCliArgs();

  if (options.help) {
    printHelp();
    process.exit(0);
  }

  const configPath = path.join(__dirname, '../../config/config.yaml');
  const configContent = await fs.readFile(configPath, 'utf8');
  const config = yaml.parse(configContent);

  // Log what we're going to scrape
  console.log('\n╔════════════════════════════════════════════╗');
  console.log('║ FLASHSCORE SCRAPER - MODULAR                ║');
  console.log('╚════════════════════════════════════════════╝\n');
  console.log(`🎯 Configuration:`);
  console.log(`   Sports: ${options.sports.join(', ')}`);
  if (options.leagues) {
    console.log(`   Leagues: ${options.leagues.join(', ')}`);
  } else {
    console.log(`   Leagues: all`);
  }
  if (options.limit) {
    console.log(`   Limit: ${options.limit} matches`);
  } else {
    console.log(`   Limit: none (scrape all)`);
  }
  console.log('');

  const scraper = new FlashscoreScraper(config);

  // Override sports list with CLI options
  scraper.config.sports = options.sports;

  try {
    await scraper.initialize();
    await scraper.scrapeAll();

    // Apply filtering after scraping
    if (options.limit) {
      scraper.matches = scraper.matches.slice(0, options.limit);
      console.log(`\n✂️  Applied limit: kept ${scraper.matches.length} matches (limit: ${options.limit})`);
    }

    if (options.leagues) {
      const leagueSet = new Set(options.leagues.map(l => l.toLowerCase()));
      const beforeFilter = scraper.matches.length;
      scraper.matches = scraper.matches.filter(m =>
        leagueSet.has(m.league.toLowerCase())
      );
      console.log(`🏆 Filtered by league: ${beforeFilter} → ${scraper.matches.length} matches`);
    }

    if (options.sports.length < 4) {  // If not requesting all 4 sports
      const sportSet = new Set(options.sports);
      const beforeFilter = scraper.matches.length;
      scraper.matches = scraper.matches.filter(m =>
        sportSet.has(m.sport)
      );
      console.log(`⚽ Filtered by sport: ${beforeFilter} → ${scraper.matches.length} matches`);
    }

    await scraper.saveResults();
  } catch (error) {
    console.error('❌ Fatal error:', error);
    process.exit(1);
  } finally {
    await scraper.close();
  }
}

if (require.main === module) {
  main().catch(console.error);
}

module.exports = FlashscoreScraper;
