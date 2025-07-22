'use client';

import { Input } from '@heroui/react';
import { useState, useRef } from 'react';

function ImageUploader() {
  const [image, setImage] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;
    if (file && file.type.startsWith('image/')) {
      setImage(file);
      // You can also handle the image upload here
      console.log('Simulated Update:', file);
    } else {
      setImage(null);
      console.warn('Please select a valid image file.');
    }
  };

  return (
    <Input type="file" accept="image/*" onChange={handleFileChange} ref={inputRef}  />

  );
}

export default ImageUploader;