import L from "leaflet";

/**
 * Movimentos de câmera que não brigam entre si.
 *
 * Dois voos simultâneos (ex.: `fitBounds` + `flyTo` no mesmo render), ou um voo começando no
 * meio de uma animação de zoom, deixam a camada vetorial (rota) desalinhada dos tiles e o mapa
 * parecendo travado. Aqui todo movimento cancela o anterior e espera o zoom em curso terminar.
 */
export function moverCamera(map: L.Map, mover: () => void): void {
  map.stop();
  // `_animatingZoom` é interno ao Leaflet 1.x, mas é o único jeito de saber se há zoom animando.
  const animando = (map as unknown as { _animatingZoom?: boolean })._animatingZoom;
  if (animando) map.once("zoomend", mover);
  else mover();
}

/** Recalcula o tamanho do mapa quando o container muda, no máximo uma vez por quadro. */
export function observarTamanho(map: L.Map): () => void {
  let quadro = 0;
  const observador = new ResizeObserver(() => {
    cancelAnimationFrame(quadro);
    quadro = requestAnimationFrame(() => map.invalidateSize({ pan: false, debounceMoveend: true }));
  });
  observador.observe(map.getContainer());
  return () => {
    cancelAnimationFrame(quadro);
    observador.disconnect();
  };
}

const posicoes = new Map<string, [number, number]>();

/**
 * Mesma tupla para a mesma coordenada. Array novo a cada render fazia o react-leaflet chamar
 * `setLatLng` em todos os marcadores a cada atualização, inclusive no meio de um zoom animado.
 */
export function posicao(lat: number, lng: number): [number, number] {
  const chave = `${lat},${lng}`;
  let p = posicoes.get(chave);
  if (!p) {
    p = [lat, lng];
    posicoes.set(chave, p);
  }
  return p;
}

const icones = new Map<string, L.DivIcon>();

/**
 * Reaproveita o mesmo `L.DivIcon` para o mesmo HTML.
 *
 * O react-leaflet troca o ícone sempre que recebe outra instância; criar um novo a cada render
 * reescrevia todos os marcadores a cada atualização (a central atualiza a cada 10 s).
 */
export function iconeEmCache(chave: string, criar: () => L.DivIcon): L.DivIcon {
  let icone = icones.get(chave);
  if (!icone) {
    icone = criar();
    icones.set(chave, icone);
    if (icones.size > 500) icones.delete(icones.keys().next().value as string);
  }
  return icone;
}
