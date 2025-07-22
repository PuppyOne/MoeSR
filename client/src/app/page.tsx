import SRForm from '@/components/sr-form';
import Version from '@/components/version';
import api from '@/lib/api';

export default async function Home() {
  return (
    <div className="font-sans grid grid-rows-[20px_1fr_20px] items-center justify-items-center min-h-screen p-8 pb-20 gap-16 sm:p-20">
      <main className="flex flex-col gap-[32px] row-start-2 items-center sm:items-start">
        <SRForm modelName={await getModels()} />
      </main>
      <footer className="row-start-3 flex gap-[24px] flex-wrap items-center justify-center text-xs text-gray-500">
        <Version />
      </footer>
    </div>
  );
}

/**
 * @example
 * {
 *   'real-esrgan': ['x4_Anime_6B-Official'],
 *   'real-hatgan': ['x4_jp_Illustration-fix1', 'x2_universal-fix1'],
 * }
 */
const getModels = async (): Promise<Record<string, string[]>> => {
  const algos = ['real-esrgan', 'real-hatgan'];

  const modelEntries = await Promise.all(
    algos.map(async algo => {
      const response = await api.get<string[]>('/model_list', {
        params: { algo },
      });
      return [algo, response.data] as const;
    })
  );

  // Convert to { [algo]: string[] }
  return Object.fromEntries(modelEntries);
};
