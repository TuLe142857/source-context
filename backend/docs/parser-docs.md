# Tree-sitter

# Language Config and Language Registry

# Convert CST to UAST
Use tree-sitter query to convert CST to UAST.

## Capture name list
Main capture name:
- `@container`
- `@definition`
- `@dependency`
- `@reference`
- `@meta`

### Capture: `@container`
- `@container.project`
- `@container.module`
- `@container.file`

### Capture: `@definition`
- `@definition.class`
- `@definition.interface`
- `@definition.enum`
- `@definition.struct`


- `@definition.function`
- `@definition.method`
- `@definition.lambda`


- `@definition.variable`
- `@definition.constant`
- `@definition.parameter`

### Capture: `@dependency`
- `@dependency.import`
- `@dependecy.export`

### Capture: `@reference`
- `@reference.call`
- `@reference.attribute`
- `@reference.type`


### Capture: `@meta`
- `@meta.doc`
- `@meta.name`
- `@meta.visibility`
- `@meta.modifier`
- ...

## UAST inheritance design
```mermaid
classDiagram
    class UASTNode{
        
    }
    class ContainerNode{
        
    }
    class DefinitionNode{
        
    }
    class DependencyNode{
        
    }
    class ReferenceNode{
        
    }
    
    class TypeDefinitionNode{
        
    }
    class FunctionNode{
        
    }
    class VariableNode{
        
    }
    
    class ImportNode{
        
    }
    class ExportNode{
        
    }
    
    class CallNode{
        
    }
    class AttributeAccessNode{
        
    }
    class TypeReferenceNode{
        
    }

    UASTNode <|-- ContainerNode
    UASTNode <|-- DefinitionNode
    UASTNode <|-- DependencyNode
    UASTNode <|-- ReferenceNode

    DefinitionNode <|-- TypeDefinitionNode
    DefinitionNode <|-- FunctionNode
    DefinitionNode <|-- VariableNode

    DependencyNode <|-- ImportNode
    DependencyNode <|-- ExportNode

    ReferenceNode <|-- CallNode
    ReferenceNode <|-- AttributeAccessNode
    ReferenceNode <|-- TypeReferenceNode
```
## UASTNode

## ContainerNode

## DefinitionNode

## DependenceNode

## ReferenceNode

