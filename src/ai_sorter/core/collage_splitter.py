"""Collage splitter.

Detect touching rectangular collage panels without database access. The detector
uses a regular grid prior and validates each grid boundary locally.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from PIL import Image, ImageOps


@dataclass(frozen=True, slots=True)
class Rectangle:
    left: int
    top: int
    right: int
    bottom: int
    @property
    def width(self) -> int: return self.right - self.left
    @property
    def height(self) -> int: return self.bottom - self.top


@dataclass(frozen=True, slots=True)
class SplitResult:
    source: Path
    image_width: int
    image_height: int
    rectangles: tuple[Rectangle, ...]
    confidence: float


@dataclass(frozen=True, slots=True)
class _Line:
    position: int
    score: float


class CollageSplitter:
    """Split rectangular collage panels without touching the database."""
    def __init__(self, *, analysis_size: int = 1024, min_piece_ratio: float = 0.05,
                 edge_threshold: float = 18.0, coverage_threshold: float = 0.20,
                 smooth_radius: int = 2) -> None:
        self.analysis_size = max(256, min(1536, int(analysis_size)))
        self.min_piece_ratio = max(0.01, min(0.40, float(min_piece_ratio)))
        self.edge_threshold = max(5.0, min(100.0, float(edge_threshold)))
        self.coverage_threshold = max(0.10, min(0.90, float(coverage_threshold)))
        self.smooth_radius = max(1, min(8, int(smooth_radius)))

    def detect(self, path: Path) -> SplitResult:
        source = Path(path).resolve()
        if not source.is_file(): raise ValueError(f"Plik nie istnieje: {source}")
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            width, height = image.size
            scaled = _resize_for_analysis(image, self.analysis_size)
            rectangles, confidence = self._detect_grid(scaled, width, height)
        return SplitResult(source, width, height, tuple(rectangles), confidence)

    def split(self, result: SplitResult, *, apply: bool = False) -> tuple[Path, ...]:
        if len(result.rectangles) < 2: return ()
        outputs = tuple(result.source.parent / f"{result.source.stem}_{i:02d}{result.source.suffix}"
                        for i in range(1, len(result.rectangles) + 1))
        if not apply: return outputs
        with Image.open(result.source) as image:
            image = ImageOps.exif_transpose(image)
            created = []
            for i, rect in enumerate(result.rectangles, 1):
                destination = _unique_output_path(outputs[i - 1])
                image.crop((rect.left, rect.top, rect.right, rect.bottom)).save(destination)
                created.append(destination)
            return tuple(created)

    def _detect_grid(self, image: Image.Image, original_width: int, original_height: int):
        gray = image.convert("L")
        x_lines = _regular_lines(gray, horizontal=False, threshold=self.edge_threshold, radius=self.smooth_radius)
        y_lines = _regular_lines(gray, horizontal=True, threshold=self.edge_threshold, radius=self.smooth_radius)
        if len(x_lines) > 6 or len(y_lines) > 6:
            return [Rectangle(0, 0, original_width, original_height)], 0.0
        xs = _dedupe([0] + [x.position for x in x_lines] + [gray.width])
        ys = _dedupe([0] + [y.position for y in y_lines] + [gray.height])
        cols, rows = len(xs) - 1, len(ys) - 1
        if cols * rows > 64:
            return [Rectangle(0, 0, original_width, original_height)], 0.0

        # The grid lines are positional priors. A seam can disappear in one
        # row/column, so validate every candidate in its local band.
        vertical = [[False] * (cols - 1) for _ in range(rows)]
        horizontal = [[False] * cols for _ in range(rows - 1)]
        scores = []
        line_by_x = {line.position: line.score for line in x_lines}
        line_by_y = {line.position: line.score for line in y_lines}
        for r in range(rows):
            for c in range(cols - 1):
                x = xs[c + 1]
                local = _local_seam(gray, x, ys[r], ys[r + 1], False, self.edge_threshold)
                prior = line_by_x.get(x, 0.0)
                score = 0.70 * local + 0.30 * prior
                vertical[r][c] = score >= self.coverage_threshold
                if vertical[r][c]: scores.append(score)
        for r in range(rows - 1):
            for c in range(cols):
                y = ys[r + 1]
                local = _local_seam(gray, y, xs[c], xs[c + 1], True, self.edge_threshold)
                prior = line_by_y.get(y, 0.0)
                score = 0.70 * local + 0.30 * prior
                horizontal[r][c] = score >= self.coverage_threshold
                if horizontal[r][c]: scores.append(score)

        components = _components(rows, cols, vertical, horizontal)
        rectangles = []
        for cells in components:
            r0, r1 = min(r for r, _ in cells), max(r for r, _ in cells)
            c0, c1 = min(c for _, c in cells), max(c for _, c in cells)
            if len(cells) == (r1-r0+1)*(c1-c0+1):
                rectangles.append(Rectangle(xs[c0], ys[r0], xs[c1+1], ys[r1+1]))
            else:
                for r, c in cells:
                    rectangles.append(Rectangle(xs[c], ys[r], xs[c+1], ys[r+1]))
        min_w, min_h = gray.width*self.min_piece_ratio, gray.height*self.min_piece_ratio
        rectangles = [r for r in rectangles if r.width >= min_w and r.height >= min_h]
        rectangles.sort(key=lambda r: (r.top, r.left))
        if len(rectangles) < 2:
            return [Rectangle(0, 0, original_width, original_height)], 0.0
        sx, sy = original_width/gray.width, original_height/gray.height
        scaled = [Rectangle(round(r.left*sx), round(r.top*sy), round(r.right*sx), round(r.bottom*sy)) for r in rectangles]
        return scaled, max(0.0, min(1.0, sum(scores)/len(scores) if scores else 0.0))


def _resize_for_analysis(image: Image.Image, limit: int) -> Image.Image:
    scale = min(1.0, limit/max(image.width, image.height))
    if scale == 1.0: return image.copy()
    return image.resize((max(1, round(image.width*scale)), max(1, round(image.height*scale))), Image.Resampling.BILINEAR)


def _regular_lines(gray: Image.Image, *, horizontal: bool, threshold: float, radius: int) -> list[_Line]:
    pixels = gray.load(); width, height = gray.size
    axis, perp = (height, width) if horizontal else (width, height)
    projection = []
    for p in range(1, axis):
        total = 0.0
        if horizontal:
            for q in range(perp): total += abs(pixels[q, p] - pixels[q, p-1])
        else:
            for q in range(perp): total += abs(pixels[p, q] - pixels[p-1, q])
        projection.append(total/perp)
    smooth = _smooth(projection, radius)
    candidates = []
    margin = max(8, round(axis*.04))
    for i in range(2, len(smooth)-2):
        p, value = i+1, smooth[i]
        if p < margin or p > axis-margin or value < threshold*.45: continue
        if value < smooth[i-1] or value < smooth[i+1]: continue
        baseline = _median(smooth[max(0,i-8):i] + smooth[i+1:min(len(smooth),i+9)])
        score = min(1.0, .55*min(1.0,value/threshold) + .45*min(1.0,value/max(1.0,baseline*2)))
        candidates.append(_Line(p, score))
    candidates.sort(key=lambda x:x.score, reverse=True)
    shortlist=[]; min_distance=max(8,round(axis*.025))
    for line in candidates:
        if all(abs(line.position-o.position)>=min_distance for o in shortlist): shortlist.append(line)
        if len(shortlist)>=14: break
    return _select_regular(shortlist, axis)


def _select_regular(candidates: list[_Line], axis: int) -> list[_Line]:
    if len(candidates)<2: return []
    best=None; min_gap=max(24,round(axis*.12))
    for n in range(2,min(5,len(candidates))+1):
        for combo in combinations(candidates,n):
            pos=sorted(x.position for x in combo); gaps=[b-a for a,b in zip(pos,pos[1:])]
            if min(gaps)<min_gap: continue
            mean=sum(gaps)/len(gaps); variation=max(gaps)-min(gaps)
            regular=max(0.0,1.0-variation/max(1.0,mean*.22))
            strength=sum(x.score for x in combo)/n
            span=(pos[-1]-pos[0])/axis
            score=.52*regular+.38*strength+.10*min(1.0,span/.45)+.06*min(n-2,2)
            if best is None or score>best[0]: best=(score,combo)
    return sorted(best[1],key=lambda x:x.position) if best and best[0]>=.55 else []


def _local_seam(gray: Image.Image, position: int, start: int, end: int, horizontal: bool, threshold: float) -> float:
    """Evaluate a narrow neighbourhood, not just one exact pixel column/row.

    Resizing and JPEG compression can move/soften a panel edge by a few pixels.
    We therefore take the strongest of +/-3 pixels and combine edge coverage
    with edge strength. This is particularly important for touching photos.
    """
    pixels=gray.load(); length=end-start
    if length<24: return 0.0
    best=0.0
    for delta in range(-3,4):
        p=position+delta
        if horizontal and not (1<=p<gray.height): continue
        if not horizontal and not (1<=p<gray.width): continue
        values=[]; strong=0
        for q in range(start,end):
            value=abs(pixels[q,p]-pixels[q,p-1]) if horizontal else abs(pixels[p,q]-pixels[p-1,q])
            values.append(float(value)); strong += value>=threshold
        coverage=strong/length
        strength=min(1.0,_median(values)/threshold)
        candidate=.60*coverage+.40*strength
        best=max(best,candidate)
    return best


def _components(rows:int, cols:int, vertical:list[list[bool]], horizontal:list[list[bool]]):
    seen=set(); result=[]
    for sr in range(rows):
        for sc in range(cols):
            if (sr,sc) in seen: continue
            stack=[(sr,sc)]; seen.add((sr,sc)); cells=[]
            while stack:
                r,c=stack.pop(); cells.append((r,c))
                if c>0 and not vertical[r][c-1] and (r,c-1) not in seen: seen.add((r,c-1)); stack.append((r,c-1))
                if c<cols-1 and not vertical[r][c] and (r,c+1) not in seen: seen.add((r,c+1)); stack.append((r,c+1))
                if r>0 and not horizontal[r-1][c] and (r-1,c) not in seen: seen.add((r-1,c)); stack.append((r-1,c))
                if r<rows-1 and not horizontal[r][c] and (r+1,c) not in seen: seen.add((r+1,c)); stack.append((r+1,c))
            result.append(cells)
    return result


def _dedupe(values:list[int])->list[int]:
    result=[]
    for value in sorted(set(values)):
        if not result or value-result[-1]>=4: result.append(value)
    return result


def _smooth(values:list[float],radius:int)->list[float]:
    return [sum(values[max(0,i-radius):min(len(values),i+radius+1)])/len(values[max(0,i-radius):min(len(values),i+radius+1)]) for i in range(len(values))]


def _median(values:list[float])->float:
    if not values: return 0.0
    ordered=sorted(values); m=len(ordered)//2
    return ordered[m] if len(ordered)%2 else (ordered[m-1]+ordered[m])/2


def _unique_output_path(path:Path)->Path:
    if not path.exists(): return path
    index=2
    while True:
        candidate=path.with_name(f"{path.stem}_{index:02d}{path.suffix}")
        if not candidate.exists(): return candidate
        index+=1
