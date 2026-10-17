/**
 * @fileoverview Google Apps Script for batch filtering field dispatch events
 * in Google Calendar and automatically applying color classifications based
 * on standardized status prefixes synced from Ragic ERP.
 */

const DISPATCH_CONFIG = {
  // Replace with your target Google Calendar ID or use 'primary'
  CALENDAR_ID: 'dispatch-team@example-company.com',
  // Number of days backward and forward from today to scan in each batch
  LOOKBACK_DAYS: 3,
  LOOKAHEAD_DAYS: 21,
  // Mapping between Ragic status prefixes and Google Calendar EventColor enums
  STATUS_COLOR_RULES: [
    { prefix: '[URGENT]', color: CalendarApp.EventColor.RED },
    { prefix: '[INSPECTION]', color: CalendarApp.EventColor.YELLOW },
    { prefix: '[MAINTENANCE]', color: CalendarApp.EventColor.BLUE },
    { prefix: '[PENDING]', color: CalendarApp.EventColor.GRAY },
    { prefix: '[COMPLETED]', color: CalendarApp.EventColor.GREEN },
  ],
};

/**
 * Main entry point for batch scanning and re-coloring dispatch calendar events.
 * Designed to be executed manually or via a time-driven Apps Script trigger.
 */
function batchClassifyDispatchEvents() {
  const calendar = CalendarApp.getCalendarById(DISPATCH_CONFIG.CALENDAR_ID);
  if (!calendar) {
    console.error('Target calendar not found: ' + DISPATCH_CONFIG.CALENDAR_ID);
    return;
  }

  const now = new Date();
  const startWindow = new Date(
    now.getTime() - DISPATCH_CONFIG.LOOKBACK_DAYS * 24 * 60 * 60 * 1000
  );
  const endWindow = new Date(
    now.getTime() + DISPATCH_CONFIG.LOOKAHEAD_DAYS * 24 * 60 * 60 * 1000
  );

  let events = [];
  try {
    events = calendar.getEvents(startWindow, endWindow);
  } catch (err) {
    console.error('Failed to retrieve calendar events: ' + err.message);
    return;
  }

  let updatedCount = 0;
  let skippedCount = 0;

  for (let i = 0; i < events.length; i++) {
    const event = events[i];
    const title = (event.getTitle() || '').trim();
    const targetColor = resolveTargetColor_(title);

    if (!targetColor) {
      skippedCount++;
      continue;
    }

    if (event.getColor() !== String(targetColor)) {
      try {
        event.setColor(targetColor);
        updatedCount++;
      } catch (err) {
        console.warn('Unable to update color for event "' + title + '": ' + err.message);
      }
    } else {
      skippedCount++;
    }
  }

  console.log(
    'Batch classification complete. Scanned: ' +
      events.length +
      ', Updated: ' +
      updatedCount +
      ', Unchanged/Skipped: ' +
      skippedCount
  );
}

/**
 * Resolves the appropriate CalendarApp.EventColor enum for a given event title.
 *
 * @param {string} title The calendar event title to inspect.
 * @return {?CalendarApp.EventColor} Matching EventColor or null if no rule matches.
 * @private
 */
function resolveTargetColor_(title) {
  for (let i = 0; i < DISPATCH_CONFIG.STATUS_COLOR_RULES.length; i++) {
    const rule = DISPATCH_CONFIG.STATUS_COLOR_RULES[i];
    if (title.indexOf(rule.prefix) === 0) {
      return rule.color;
    }
  }
  return null;
}
