import { redirect } from 'next/navigation';

export default function TradePage() {
  redirect('/dashboard/strategy-setting?tab=positions');
}
