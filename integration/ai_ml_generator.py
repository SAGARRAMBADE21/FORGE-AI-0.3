"""AI/ML integration generator."""

import logging

logger = logging.getLogger(__name__)


class AIMLGenerator:
    """Generate AI/ML integration code."""

    def generate_rag_infrastructure(self) -> dict[str, str]:
        """Generate RAG infrastructure code."""
        return {
            "src/ai/rag.ts": """
import { OpenAIEmbeddings } from '@langchain/openai';
import { PineconeStore } from '@langchain/pinecone';
import { Pinecone } from '@pinecone-database/pinecone';
import { RecursiveCharacterTextSplitter } from 'langchain/text_splitter';
import { Document } from 'langchain/document';

const embeddings = new OpenAIEmbeddings({
  openAIApiKey: process.env.OPENAI_API_KEY,
});

const pinecone = new Pinecone({
  apiKey: process.env.PINECONE_API_KEY!,
});

const INDEX_NAME = process.env.PINECONE_INDEX || 'documents';

export async function indexDocuments(
  documents: { content: string; metadata: Record<string, any> }[]
): Promise<void> {
  const textSplitter = new RecursiveCharacterTextSplitter({
    chunkSize: 1000,
    chunkOverlap: 200,
  });

  const docs = await Promise.all(
    documents.map(async (doc) => {
      const chunks = await textSplitter.splitText(doc.content);
      return chunks.map(
        (chunk) => new Document({ pageContent: chunk, metadata: doc.metadata })
      );
    })
  );

  const flatDocs = docs.flat();

  const index = pinecone.Index(INDEX_NAME);
  await PineconeStore.fromDocuments(flatDocs, embeddings, {
    pineconeIndex: index,
  });
}

export async function searchDocuments(
  query: string,
  topK: number = 5
): Promise<Document[]> {
  const index = pinecone.Index(INDEX_NAME);
  const vectorStore = await PineconeStore.fromExistingIndex(embeddings, {
    pineconeIndex: index,
  });

  return vectorStore.similaritySearch(query, topK);
}

export async function generateWithContext(
  query: string,
  systemPrompt?: string
): Promise<string> {
  const relevantDocs = await searchDocuments(query);
  const context = relevantDocs.map((d) => d.pageContent).join('\\n\\n');

  // Use your preferred LLM here
  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: 'gpt-4-turbo-preview',
      messages: [
        { role: 'system', content: systemPrompt || 'You are a helpful assistant.' },
        { role: 'user', content: `Context:\\n${context}\\n\\nQuestion: ${query}` },
      ],
    }),
  });

  const data = await response.json();
  return data.choices[0].message.content;
}
""",
            "src/ai/langchain.ts": """
import { ChatOpenAI } from '@langchain/openai';
import { ChatAnthropic } from '@langchain/anthropic';
import { HumanMessage, SystemMessage } from '@langchain/core/messages';
import { StringOutputParser } from '@langchain/core/output_parsers';
import { RunnableSequence } from '@langchain/core/runnables';

// Initialize models
export const openai = new ChatOpenAI({
  modelName: 'gpt-4-turbo-preview',
  temperature: 0.7,
  openAIApiKey: process.env.OPENAI_API_KEY,
});

export const anthropic = new ChatAnthropic({
  modelName: 'claude-3-opus-20240229',
  temperature: 0.7,
  anthropicApiKey: process.env.ANTHROPIC_API_KEY,
});

// Simple chain
export const simpleChain = RunnableSequence.from([
  openai,
  new StringOutputParser(),
]);

// Chat function
export async function chat(
  message: string,
  systemPrompt?: string,
  model: 'openai' | 'anthropic' = 'openai'
): Promise<string> {
  const llm = model === 'openai' ? openai : anthropic;
  
  const messages = [
    new SystemMessage(systemPrompt || 'You are a helpful assistant.'),
    new HumanMessage(message),
  ];

  const response = await llm.invoke(messages);
  return response.content as string;
}

// Structured output
export async function generateStructured<T>(
  prompt: string,
  schema: any
): Promise<T> {
  const structuredLlm = openai.withStructuredOutput(schema);
  return structuredLlm.invoke(prompt) as Promise<T>;
}
""",
        }

    def generate_langgraph_agent(self) -> dict[str, str]:
        """Generate LangGraph agent code."""
        return {
            "src/ai/agent.ts": """
import { StateGraph, END } from '@langchain/langgraph';
import { ChatOpenAI } from '@langchain/openai';
import { HumanMessage, AIMessage, BaseMessage } from '@langchain/core/messages';
import { ToolExecutor } from '@langchain/langgraph/prebuilt';

// Define state
interface AgentState {
  messages: BaseMessage[];
  next: string;
}

// Initialize model
const model = new ChatOpenAI({
  modelName: 'gpt-4-turbo-preview',
  temperature: 0,
});

// Define tools
const tools = [
  // Add your tools here
];

const toolExecutor = new ToolExecutor({ tools });

// Define nodes
async function agent(state: AgentState): Promise<Partial<AgentState>> {
  const response = await model.invoke(state.messages);
  return { messages: [...state.messages, response] };
}

async function toolNode(state: AgentState): Promise<Partial<AgentState>> {
  const lastMessage = state.messages[state.messages.length - 1] as AIMessage;
  
  if (!lastMessage.tool_calls?.length) {
    return { next: END };
  }

  const toolResults = await Promise.all(
    lastMessage.tool_calls.map((call) =>
      toolExecutor.invoke({ tool: call.name, toolInput: call.args })
    )
  );

  return {
    messages: [...state.messages, ...toolResults],
    next: 'agent',
  };
}

function shouldContinue(state: AgentState): string {
  const lastMessage = state.messages[state.messages.length - 1] as AIMessage;
  return lastMessage.tool_calls?.length ? 'tools' : END;
}

// Build graph
const workflow = new StateGraph<AgentState>({
  channels: {
    messages: { value: (a, b) => [...a, ...b], default: () => [] },
    next: { value: (a, b) => b ?? a, default: () => 'agent' },
  },
});

workflow.addNode('agent', agent);
workflow.addNode('tools', toolNode);

workflow.setEntryPoint('agent');
workflow.addConditionalEdges('agent', shouldContinue);
workflow.addEdge('tools', 'agent');

export const agentGraph = workflow.compile();

// Run agent
export async function runAgent(input: string): Promise<string> {
  const result = await agentGraph.invoke({
    messages: [new HumanMessage(input)],
    next: 'agent',
  });

  const lastMessage = result.messages[result.messages.length - 1];
  return lastMessage.content as string;
}
""",
        }
