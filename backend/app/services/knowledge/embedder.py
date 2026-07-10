import logging
from fastembed import TextEmbedding

logger = logging.getLogger(__name__)

# Lazily initialized model instance
_model = None

# Global configuration variables optimized for Render Free Tier (512 MB RAM)
# Disabling the C++ memory arena and limiting thread count prevents OOM crashes on CPU containers.
ONNX_THREADS = 2
ONNX_ARENA = False
ONNX_GRAPH_OPT = "BASIC"

class EmbeddingGenerationError(Exception):
    """Exception raised when embedding generation fails."""
    pass

def get_embedding_model() -> TextEmbedding:
    """Returns the lazily initialized local FastEmbed TextEmbedding instance with patched ONNX session options."""
    global _model
    if _model is None:
        import onnxruntime as ort
        
        # Resolve graph optimization level
        graph_opt = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        if ONNX_GRAPH_OPT == "BASIC":
            graph_opt = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        elif ONNX_GRAPH_OPT == "DISABLE":
            graph_opt = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
            
        original_init = ort.InferenceSession.__init__
        
        def patched_init(self, model_path, sess_options=None, *args, **kwargs):
            if sess_options is None:
                sess_options = ort.SessionOptions()
            
            # Apply configured threads count
            if ONNX_THREADS is not None:
                sess_options.intra_op_num_threads = ONNX_THREADS
                sess_options.inter_op_num_threads = ONNX_THREADS
                
            # Apply configured CPU memory arena
            sess_options.enable_cpu_mem_arena = ONNX_ARENA
            
            # Apply configured graph optimization level
            sess_options.graph_optimization_level = graph_opt
            
            # Delegate to original initialization
            original_init(self, model_path, sess_options=sess_options, *args, **kwargs)
            
        # Hook InferenceSession.__init__
        ort.InferenceSession.__init__ = patched_init
        
        logger.info(f"Initializing local FastEmbed model BAAI/bge-small-en-v1.5 (Threads={ONNX_THREADS}, Arena={ONNX_ARENA}, GraphOpt={ONNX_GRAPH_OPT})...")
        _model = TextEmbedding()
        
    return _model

def verify_embeddings_status() -> None:
    """FastEmbed is always available since it runs locally inside the process context."""
    pass

def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generates embeddings locally using FastEmbed.
    Does not make any external network requests.
    """
    try:
        model = get_embedding_model()
        # model.embed returns a generator of numpy arrays
        embeddings_generator = model.embed(texts)
        # Convert generator of arrays to list of lists of standard floats
        return [list(map(float, emb)) for emb in embeddings_generator]
    except Exception as e:
        logger.error(f"Local embedding generation failed: {str(e)}")
        raise EmbeddingGenerationError(f"Local embedding generation failed. Error: {str(e)}")
