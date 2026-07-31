import { redirect } from 'next/navigation';

export default function GridPage() {
  redirect('/dashboard/strategy-setting?tab=grid');
}
