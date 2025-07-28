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
    <div className="font-sans grid grid-rows-[20px_1fr_20px] items-center justify-items-center min-h-screen p-8 pb-20 gap-16 sm:p-20">
      <main className="flex flex-col gap-[32px] row-start-2 items-center sm:items-start">
        <Image
          src={data.outputUrl}
          alt="Processed Image"
          className="w-full min-w-xs max-w-md"
        />
      </main>
    </div>
  );
}
