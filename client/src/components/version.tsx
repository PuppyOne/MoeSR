'use client';
import { Tooltip } from '@heroui/react';

export default function Version() {
  return (
    <Tooltip content="别问为什么bug多，这个版本号你还不认识吗？" delay={500}>
      v0.0.1-nightly-alpha-rc0-SNAPSHOT-UNSTABLE-DEV
    </Tooltip>
  );
}
