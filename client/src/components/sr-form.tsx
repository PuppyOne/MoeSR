'use client';
import api from '@/lib/api';
import {
  Form,
  Input,
  Select,
  SelectSection,
  SelectItem,
  Slider,
  Checkbox,
  Button,
  addToast,
} from '@heroui/react';
import { isAxiosError } from 'axios';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export default function SRForm({
  modelName,
}: {
  modelName: Record<string, string[]>;
}) {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number>();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const { currentTarget: form } = e;
    console.log(Object.fromEntries(new FormData(form)));

    setIsLoading(true);

    try {
      const { data } = await api.post('/run_process', form, {
        onUploadProgress: ({ progress }) => {
          setUploadProgress(progress);
        },
      });

      addToast({
        title: 'Success',
        description: `Image processed successfully! Saved to ${data.outputUrl}.`,
        color: 'success',
      });
      router.push(`/tasks/${data.id}`);
    } catch (error) {
      addToast({
        title: 'Error',
        description:
          error instanceof Error
            ? (isAxiosError(error) && error.response?.data?.error) ??
              error.message
            : 'An unexpected error occurred.',
        color: 'danger',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Form className="flex gap-5" onSubmit={handleSubmit}>
      <Input
        name="image"
        type="file"
        accept="image/*"
        label="Input Image"
        labelPlacement="outside"
        isDisabled={isLoading}
        isRequired
      />
      <Select
        name="model"
        label="Model"
        labelPlacement="outside"
        placeholder="Select a model"
        isDisabled={isLoading}
        isRequired
        disallowEmptySelection
      >
        {Object.entries(modelName).map(([algo, models]) => (
          <SelectSection key={algo} title={algo}>
            {models.map(model => (
              <SelectItem key={`${algo}:${model}`}>{model}</SelectItem>
            ))}
          </SelectSection>
        ))}
      </Select>
      <Slider
        name="scale"
        label="Scale"
        defaultValue={0.4}
        maxValue={16}
        minValue={2}
        marks={[
          {
            value: 2,
            label: 'x2',
          },
          {
            value: 4,
            label: 'x4',
          },
          {
            value: 8,
            label: 'x8',
          },
          {
            value: 16,
            label: 'x16',
          },
        ]}
        getValue={value => `x${value}`}
        isDisabled={isLoading}
      />
      <Checkbox name="isSkipAlpha" value="true" isDisabled={isLoading}>
        Skip Alpha Channel
      </Checkbox>
      <Button color="primary" type="submit" isLoading={isLoading} fullWidth>
        {isLoading
          ? uploadProgress === undefined
            ? 'Starting...'
            : uploadProgress >= 1
            ? 'Processing...'
            : `Uploading... ${Math.round(uploadProgress * 100)}%`
          : 'Start'}
      </Button>
    </Form>
  );
}
