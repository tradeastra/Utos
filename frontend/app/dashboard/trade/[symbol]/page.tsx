import { redirect } from 'next/navigation';

export default function CoinDetailPage() {
  redirect('/dashboard/strategy-setting?tab=positions');
}
