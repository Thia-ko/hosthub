"use client";

import { Bot, History, MessageCircle, Send, Webhook, type LucideIcon } from "lucide-react";
import { useMemo } from "react";
import {
  Background,
  BackgroundVariant,
  Handle,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

/** Purely illustrative diagram of the message -> AI reply pipeline. Fixed layout, no drag/zoom/
 * selection - it exists to make the "how it works" story legible at a glance, not to reflect
 * live execution state. Shown identically above the guided wizard and the advanced text editor. */
const STEPS: { title: string; description: string; icon: LucideIcon }[] = [
  { title: "Lead envia mensagem", description: "O cliente escreve no WhatsApp", icon: MessageCircle },
  { title: "Hosthub recebe", description: "Identifica a instancia e a conversa", icon: Webhook },
  { title: "Contexto e historico", description: "Reune o historico e os dados do negocio", icon: History },
  { title: "IA gera a resposta", description: "Usa o prompt configurado abaixo", icon: Bot },
  { title: "Resposta enviada", description: "A mensagem volta para o Lead", icon: Send },
];

function PipelineNode({ data }: NodeProps<Node<{ title: string; description: string; icon: LucideIcon }>>) {
  const Icon = data.icon;
  return (
    <div className="flex w-56 items-start gap-3 rounded-xl border bg-card p-3 shadow-sm">
      <Handle type="target" position={Position.Left} className="!opacity-0" />
      <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/15 text-primary">
        <Icon className="size-4.5" />
      </span>
      <div className="flex flex-col gap-0.5">
        <p className="text-sm font-medium leading-tight">{data.title}</p>
        <p className="text-xs leading-tight text-muted-foreground">{data.description}</p>
      </div>
      <Handle type="source" position={Position.Right} className="!opacity-0" />
    </div>
  );
}

const nodeTypes = { pipeline: PipelineNode };

export function AiPipelinePreview() {
  const nodes = useMemo<Node[]>(
    () =>
      STEPS.map((step, index) => ({
        id: String(index),
        type: "pipeline",
        position: { x: index * 264, y: index % 2 === 0 ? 0 : 68 },
        data: step,
        draggable: false,
        selectable: false,
        className: "animate-in fade-in slide-in-from-bottom-2 duration-500 fill-mode-both",
        style: { animationDelay: `${index * 120}ms` },
      })),
    []
  );

  const edges = useMemo<Edge[]>(
    () =>
      STEPS.slice(1).map((_, index) => ({
        id: `e${index}-${index + 1}`,
        source: String(index),
        target: String(index + 1),
        type: "smoothstep",
        animated: true,
        style: { stroke: "var(--primary)", strokeWidth: 2 },
      })),
    []
  );

  return (
    <div className="h-56 w-full overflow-hidden rounded-xl border bg-muted/30">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnDrag={false}
        panOnScroll={false}
        zoomOnScroll={false}
        zoomOnPinch={false}
        zoomOnDoubleClick={false}
        preventScrolling={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} className="opacity-40" />
      </ReactFlow>
    </div>
  );
}
