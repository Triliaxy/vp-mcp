package com.brunnen.vp.mcp.util;

import com.vp.plugin.diagram.IDiagramElement;
import com.vp.plugin.diagram.IDiagramUIModel;
import com.vp.plugin.diagram.IShapeUIModel;
import com.vp.plugin.model.IModelElement;
import com.vp.plugin.model.IProject;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

/** Deletes through VP's supported APIs and verifies the resulting project state. */
public final class DiagramElementDeletion {
  private DiagramElementDeletion() {}

  public static void removeView(IDiagramUIModel diagram, String elementName) {
    IDiagramElement element = findUniqueElement(diagram, elementName);
    String viewId = element.getId();
    // IDiagramUIModel.removeDiagramElement is deprecated and can leave the view alive.
    element.deleteViewOnly();
    if (containsView(diagram, viewId)) {
      throw new IllegalStateException(
          "Visual Paradigm did not remove the diagram view: " + elementName);
    }
  }

  public static void deleteModel(IProject project, IDiagramUIModel diagram, String elementName) {
    IDiagramElement element = findUniqueElement(diagram, elementName);
    IModelElement model = element.getModelElement();
    if (model == null) {
      throw new IllegalArgumentException("Element has no underlying model: " + elementName);
    }
    String modelId = model.getId();
    Map<IDiagramUIModel, List<String>> affectedViews = new HashMap<>();
    Iterator<?> diagrams = project.diagramIterator();
    while (diagrams.hasNext()) {
      IDiagramUIModel current = (IDiagramUIModel) diagrams.next();
      List<String> ids = new ArrayList<>();
      Iterator<?> views = current.diagramElementIterator();
      while (views.hasNext()) {
        IDiagramElement view = (IDiagramElement) views.next();
        IModelElement viewModel = view.getModelElement();
        if (viewModel != null && modelId.equals(viewModel.getId())) {
          ids.add(view.getId());
        }
      }
      affectedViews.put(current, ids);
    }
    // Model deletion is explicit; unlike removing one view it affects every diagram.
    model.delete();
    Iterator<?> models = project.allLevelModelElementIterator();
    while (models.hasNext()) {
      IModelElement remaining = (IModelElement) models.next();
      if (modelId.equals(remaining.getId())) {
        throw new IllegalStateException("Visual Paradigm did not delete the model: " + elementName);
      }
    }
    for (Map.Entry<IDiagramUIModel, List<String>> entry : affectedViews.entrySet()) {
      for (String viewId : entry.getValue()) {
        if (containsView(entry.getKey(), viewId)) {
          throw new IllegalStateException("A view of the deleted model remains: " + elementName);
        }
      }
    }
  }

  private static IDiagramElement findUniqueElement(IDiagramUIModel diagram, String elementName) {
    if (elementName == null || elementName.trim().isEmpty()) {
      throw new IllegalArgumentException("Element name must not be blank");
    }
    IDiagramElement found = null;
    Iterator<?> views = diagram.diagramElementIterator();
    while (views.hasNext()) {
      IDiagramElement view = (IDiagramElement) views.next();
      IModelElement model = view.getModelElement();
      boolean matches = model != null && elementName.equals(model.getName());
      if (view instanceof IShapeUIModel) {
        matches |= elementName.equals(((IShapeUIModel) view).getCustomText());
      }
      if (matches) {
        if (found != null) {
          throw new IllegalArgumentException(
              "More than one element has this name on the diagram: " + elementName);
        }
        found = view;
      }
    }
    if (found == null) {
      throw new IllegalArgumentException("Element not found on diagram: " + elementName);
    }
    return found;
  }

  private static boolean containsView(IDiagramUIModel diagram, String viewId) {
    Iterator<?> views = diagram.diagramElementIterator();
    while (views.hasNext()) {
      if (viewId.equals(((IDiagramElement) views.next()).getId())) {
        return true;
      }
    }
    return false;
  }
}
