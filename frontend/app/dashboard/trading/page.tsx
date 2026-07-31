import { redirect } from 'next/navigation';

export default function TradingPage() {
  redirect('/dashboard/trade?tab=bots');
}
