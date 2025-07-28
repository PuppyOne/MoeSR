import { Image } from '@heroui/react';
import api from '@/lib/api';

export default async function Task({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { data } = await api.get<{ outputUrl: string }>(`/tasks/${id}`);
  return (
    <Image
      src={data.outputUrl}
      alt="Processed Image"
      className="w-full min-w-xs max-w-md"
    />
  );
}
