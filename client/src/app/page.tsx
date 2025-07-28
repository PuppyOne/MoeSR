import SRForm from '@/components/sr-form';
import api from '@/lib/api';

export default async function Home() {
  return <SRForm modelName={await getModels()} />;
}

/**
 * @example
 * {
 *   'real-esrgan': ['x4_Anime_6B-Official'],
 *   'real-hatgan': ['x4_jp_Illustration-fix1', 'x2_universal-fix1'],
 * }
 */
const getModels = async (): Promise<Record<string, string[]>> => {
  const { data } = await api.get<Record<string, string[]>>('/models');
  return data;
};
