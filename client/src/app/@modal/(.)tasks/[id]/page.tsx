'use client';
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Image,
  Link,
} from '@heroui/react';
import api from '@/lib/api';
import { use, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

export default function TaskModal({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const router = useRouter();
  const { id } = use(params);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  useEffect(() => {
    const fetchImage = async () => {
      const {
        data: { outputUrl },
      } = await api.get<{ outputUrl: string }>(`/tasks/${id}`);

      setImageUrl(outputUrl);
    };

    fetchImage();
  }, [id]);

  return (
    <Modal defaultOpen hideCloseButton onClose={() => router.back()}>
      <ModalContent>
        {onClose => (
          <>
            <ModalHeader>Processed Image</ModalHeader>
            <ModalBody className="flex items-center">
              <Image
                src={imageUrl!}
                alt="Processed Image"
                className="w-full min-w-xs max-w-md"
              />
            </ModalBody>
            <ModalFooter>
              <Button color="danger" variant="light" onPress={onClose}>
                Close
              </Button>
              <Button color="primary" as={Link} href={imageUrl!}>
                Download
              </Button>
            </ModalFooter>
          </>
        )}
      </ModalContent>
    </Modal>
  );
}
