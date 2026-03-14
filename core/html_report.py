import json


def _page(title, text, body_html, script):
    return f"""<!doctype html>
<html>
<body style="font-family:sans-serif">

<h2>{title}</h2>

<p style="white-space:pre-line; max-width:1100px">{text}</p>

{body_html}

<script>
{script}
</script>

</body>
</html>
"""


def render_page(title, text, charts):
    canvases = []
    js = []

    js.append(
        """
function setupCanvas(id){
  const canvas=document.getElementById(id)
  const ctx=canvas.getContext("2d")
  ctx.font="14px sans-serif"
  ctx.strokeStyle="#000"
  ctx.fillStyle="#000"
  return {canvas,ctx}
}

function axes(ctx,left,right,plotTop,plotBottom,width){
  ctx.beginPath()
  ctx.moveTo(left,plotTop)
  ctx.lineTo(left,plotBottom)
  ctx.lineTo(width-right,plotBottom)
  ctx.stroke()
}

function yTicks(ctx,left,plotTop,plotBottom,plotH,maxV,suffix,dec){
  for(let i=0;i<=5;i++){
    const y=plotBottom-(plotH*i/5)
    const v=maxV*i/5
    ctx.beginPath()
    ctx.moveTo(left-6,y)
    ctx.lineTo(left,y)
    ctx.stroke()
    ctx.fillText(v.toFixed(dec)+suffix,18,y+4)
  }
}

function xTicks(ctx,left,plotBottom,plotW,times,maxT){
  const step=Math.max(1,Math.floor(times.length/10))
  ctx.textAlign="center"
  for(let i=0;i<times.length;i+=step){
    const x=left+(plotW*(times[i]/maxT))
    ctx.beginPath()
    ctx.moveTo(x,plotBottom)
    ctx.lineTo(x,plotBottom+6)
    ctx.stroke()
    ctx.fillText(times[i]+"s",x,plotBottom+18)
  }
  ctx.textAlign="left"
}

function onset(ctx,onset,left,plotW,maxT,plotTop,plotBottom,width){
  if(onset===null)return
  const x=left+(plotW*(onset/maxT))
  ctx.strokeStyle="red"
  ctx.beginPath()
  ctx.moveTo(x,plotTop)
  ctx.lineTo(x,plotBottom)
  ctx.stroke()
  ctx.fillStyle="red"
  ctx.fillText("Onset ~"+onset+"s",Math.min(x+6,width-140),plotTop+14)
  ctx.strokeStyle="#000"
  ctx.fillStyle="#000"
}

function shortenLabel(label){
  if(label.length <= 24) return label

  let s = label
  s = s.replace("Unknown ", "")
  s = s.replace(" DSCP ", " ")
  s = s.replace(" (Port ", " ")
  s = s.replace(")", "")

  if(s.length <= 24) return s
  return s.slice(0, 21) + "..."
}
"""
    )

    js.append(
        """
function drawTimeBars(chart){
  const s=setupCanvas(chart.id)
  const c=s.canvas
  const g=s.ctx

  const left=80
  const right=40
  const plotTop=30
  const plotBottom=c.height-80

  const plotW=c.width-left-right
  const plotH=plotBottom-plotTop

  const times=chart.x
  const vals=chart.y

  const maxT=Math.max(...times,1)
  const maxV=Math.max(...vals,1)

  axes(g,left,right,plotTop,plotBottom,c.width)
  g.fillText(chart.title,left,16)

  yTicks(g,left,plotTop,plotBottom,plotH,maxV,chart.y_suffix||"",chart.y_decimals||0)
  xTicks(g,left,plotBottom,plotW,times,maxT)

  for(let i=0;i<times.length;i++){
    const x=left+(plotW*(times[i]/maxT))
    const y=plotBottom-(vals[i]/maxV)*plotH

    g.fillStyle=chart.color||"#6b7280"
    g.fillRect(x-3,y,6,Math.max(2,plotBottom-y))
  }

  onset(g,chart.onset,left,plotW,maxT,plotTop,plotBottom,c.width)

  if(chart.footer)
    g.fillText(chart.footer,left,c.height-18)
}
"""
    )

    js.append(
        """
function drawTimeBarsDual(chart){
  const s=setupCanvas(chart.id)
  const c=s.canvas
  const g=s.ctx

  const left=80
  const right=40
  const plotTop=30
  const plotBottom=c.height-80

  const plotW=c.width-left-right
  const plotH=plotBottom-plotTop

  const times=chart.x
  const avg=chart.y
  const max=chart.y2

  const maxT=Math.max(...times,1)
  const maxV=Math.max(...max.filter(v=>v>0),1)

  axes(g,left,right,plotTop,plotBottom,c.width)
  g.fillText(chart.title,left,16)

  yTicks(g,left,plotTop,plotBottom,plotH,maxV,chart.y_suffix||"",chart.y_decimals||0)
  xTicks(g,left,plotBottom,plotW,times,maxT)

  for(let i=0;i<times.length;i++){
    const x=left+(plotW*(times[i]/maxT))

    if(chart.highlight_y && chart.highlight_y[i] > (chart.highlight_threshold || 0)){
      g.fillStyle=chart.highlight_color||"rgba(255,0,0,0.08)"
      g.fillRect(x-4,plotTop,8,plotH)
    }

    const avgY=plotBottom-(avg[i]/maxV)*plotH
    const maxY=plotBottom-(max[i]/maxV)*plotH

    g.fillStyle=chart.color1||"#6b7280"
    g.fillRect(x-2,avgY,4,Math.max(2,plotBottom-avgY))

    g.fillStyle=chart.color2||"#b00020"
    g.fillRect(x-1,maxY,2,6)
  }

  onset(g,chart.onset,left,plotW,maxT,plotTop,plotBottom,c.width)

  if(chart.footer)
    g.fillText(chart.footer,left,c.height-18)
}
"""
    )

    js.append(
        """
function drawHistogram(chart){
  const s=setupCanvas(chart.id)
  const c=s.canvas
  const g=s.ctx

  const left=80
  const right=40
  const plotTop=50
  const plotBottom=c.height-160

  const plotW=c.width-left-right
  const plotH=plotBottom-plotTop

  const vals=chart.values
  const labels=chart.labels
  const colors=chart.colors||[]

  const maxV=Math.max(...vals,1)

  axes(g,left,right,plotTop,plotBottom,c.width)
  g.fillText(chart.title,left,16)

  yTicks(g,left,plotTop,plotBottom,plotH,maxV,"",0)

  const histLeft=left+40
  const histW=c.width-histLeft-right
  const count=Math.max(vals.length,1)
  const barGap=Math.max(12, Math.min(40, Math.floor(histW / (count * 3))))
  const barW=Math.max(24, Math.min(120, Math.floor((histW - barGap*(count-1)) / count)))

  for(let i=0;i<vals.length;i++){
    const x=histLeft+i*(barW+barGap)
    const y=plotBottom-(vals[i]/maxV)*plotH

    g.fillStyle=colors[i]||"#6b7280"
    g.fillRect(x,y,barW,Math.max(2,plotBottom-y))

    g.fillStyle="#000"
    g.textAlign="center"
    g.fillText(vals[i],x+barW/2,y-6)

    const label=shortenLabel(labels[i])
    g.save()
    g.translate(x+barW/2, plotBottom+10)

    const rotate = label.length > 12 || vals.length > 5
    if(rotate){
      g.rotate(-Math.PI/4)
      g.textAlign="right"
      g.fillText(label,0,0)
    }else{
      g.textAlign="center"
      g.fillText(label,0,12)
    }
    g.restore()
  }

  g.textAlign="left"

  if(chart.footer)
    g.fillText(chart.footer,left,c.height-24)
}
"""
    )

    for i, chart in enumerate(charts, start=1):
        cid = f"chart_{i}"
        height = chart.get("height", 260)

        canvases.append(
            f'<canvas id="{cid}" width="1100" height="{height}" style="margin-top:16px; margin-bottom:26px;"></canvas>'
        )

        chart_data = dict(chart)
        chart_data["id"] = cid

        js.append(f"const data_{i} = {json.dumps(chart_data)};")

        if chart["type"] == "time_bars":
            js.append(f"drawTimeBars(data_{i});")
        elif chart["type"] == "time_bars_dual":
            js.append(f"drawTimeBarsDual(data_{i});")
        elif chart["type"] == "histogram":
            js.append(f"drawHistogram(data_{i});")

    return _page(title, text, "\n".join(canvases), "\n".join(js))