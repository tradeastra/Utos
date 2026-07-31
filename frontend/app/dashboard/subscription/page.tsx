import { redirect } from 'next/navigation';

export default function SubscriptionPage() {
  redirect('/dashboard/billing?tab=plans');
}
