import { Button, Image, Link } from '@heroui/react';
import { notFound } from 'next/navigation';
import { HttpStatusCode, isAxiosError } from 'axios';
import api from '@/lib/api';

export default async function Task({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  try {
    const { data } = await api.get<{ outputUrl: string }>(`/tasks/${id}`);

    return (
      <>
        <Image
          src={data.outputUrl}
          alt="Processed Image"
          className="w-full min-w-xs max-w-md"
        />
        <Button color="primary" as={Link} href={data.outputUrl} fullWidth>
          Download
        </Button>
      </>
    );
  } catch (error) {
    if (isAxiosError(error) && error.status == HttpStatusCode.NotFound)
      notFound();

    throw error;
  }
}
