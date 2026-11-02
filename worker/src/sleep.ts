const FALL_ASLEEP_MINUTES = 15;
const CYCLE_MINUTES = 90;
const timeFormatter = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
});

export function formatSleepMessage(now: Date = new Date()): string {
  const lines = [
    '🌙 Giờ thức dậy ước tính nếu đi ngủ bây giờ',
    'Đã cộng 15 phút chờ vào giấc ngủ.',
    '',
  ];
  for (let cycles = 1; cycles <= 5; cycles++) {
    const sleepMinutes = cycles * CYCLE_MINUTES;
    const wakeUp = new Date(now.getTime() + (FALL_ASLEEP_MINUTES + sleepMinutes) * 60_000);
    const duration = [
      `${Math.floor(sleepMinutes / 60)} giờ`,
      ...(sleepMinutes % 60 ? [`${sleepMinutes % 60} phút`] : []),
    ].join(' ');
    lines.push(`• ${cycles} chu kỳ — ngủ ${duration}: <code>${timeFormatter.format(wakeUp)}</code> thức dậy`);
  }
  return lines.join('\n');
}
