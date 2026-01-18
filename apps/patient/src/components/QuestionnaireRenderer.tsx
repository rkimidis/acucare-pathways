'use client';

import { useState, useEffect } from 'react';
import styles from './QuestionnaireRenderer.module.css';

interface FieldOption {
  value: string | number;
  label: string;
}

interface QuestionnaireField {
  id: string;
  type: 'text' | 'textarea' | 'number' | 'boolean' | 'select' | 'multiselect' | 'date';
  label: string;
  description?: string;
  required?: boolean;
  options?: FieldOption[];
  placeholder?: string;
  min?: number;
  max?: number;
  section?: string;
}

interface QuestionnaireSchema {
  title?: string;
  description?: string;
  sections?: { id: string; title: string; description?: string }[];
  fields: QuestionnaireField[];
}

interface QuestionnaireRendererProps {
  schema: QuestionnaireSchema;
  answers: Record<string, unknown>;
  onChange: (answers: Record<string, unknown>) => void;
  errors?: Record<string, string>;
  disabled?: boolean;
}

export default function QuestionnaireRenderer({
  schema,
  answers,
  onChange,
  errors = {},
  disabled = false,
}: QuestionnaireRendererProps) {
  const handleChange = (fieldId: string, value: unknown) => {
    onChange({
      ...answers,
      [fieldId]: value,
    });
  };

  const renderField = (field: QuestionnaireField) => {
    const error = errors[field.id];
    const value = answers[field.id];

    switch (field.type) {
      case 'text':
        return (
          <input
            type="text"
            id={field.id}
            value={(value as string) || ''}
            onChange={(e) => handleChange(field.id, e.target.value)}
            placeholder={field.placeholder}
            className={`${styles.input} ${error ? styles.inputError : ''}`}
            disabled={disabled}
            required={field.required}
          />
        );

      case 'textarea':
        return (
          <textarea
            id={field.id}
            value={(value as string) || ''}
            onChange={(e) => handleChange(field.id, e.target.value)}
            placeholder={field.placeholder}
            className={`${styles.textarea} ${error ? styles.inputError : ''}`}
            disabled={disabled}
            required={field.required}
            rows={4}
          />
        );

      case 'number':
        return (
          <input
            type="number"
            id={field.id}
            value={(value as number) ?? ''}
            onChange={(e) =>
              handleChange(
                field.id,
                e.target.value ? Number(e.target.value) : null
              )
            }
            min={field.min}
            max={field.max}
            className={`${styles.input} ${error ? styles.inputError : ''}`}
            disabled={disabled}
            required={field.required}
          />
        );

      case 'boolean':
        return (
          <div className={styles.booleanGroup}>
            <label className={styles.radioLabel}>
              <input
                type="radio"
                name={field.id}
                checked={value === true}
                onChange={() => handleChange(field.id, true)}
                disabled={disabled}
              />
              Yes
            </label>
            <label className={styles.radioLabel}>
              <input
                type="radio"
                name={field.id}
                checked={value === false}
                onChange={() => handleChange(field.id, false)}
                disabled={disabled}
              />
              No
            </label>
          </div>
        );

      case 'select':
        return (
          <select
            id={field.id}
            value={value !== undefined && value !== null ? String(value) : ''}
            onChange={(e) => {
              if (!e.target.value) {
                handleChange(field.id, null);
                return;
              }
              // Find the original option to preserve its value type (number vs string)
              const selectedOption = field.options?.find(
                (opt) => String(opt.value) === e.target.value
              );
              handleChange(field.id, selectedOption?.value ?? e.target.value);
            }}
            className={`${styles.select} ${error ? styles.inputError : ''}`}
            disabled={disabled}
            required={field.required}
          >
            <option value="">Select an option...</option>
            {field.options?.map((opt) => (
              <option key={String(opt.value)} value={String(opt.value)}>
                {opt.label}
              </option>
            ))}
          </select>
        );

      case 'multiselect':
        return (
          <div className={styles.checkboxGroup}>
            {field.options?.map((opt) => (
              <label key={opt.value} className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={
                    Array.isArray(value) && value.includes(opt.value)
                  }
                  onChange={(e) => {
                    const currentValues = (value as string[]) || [];
                    const newValues = e.target.checked
                      ? [...currentValues, opt.value]
                      : currentValues.filter((v) => v !== opt.value);
                    handleChange(field.id, newValues);
                  }}
                  disabled={disabled}
                />
                {opt.label}
              </label>
            ))}
          </div>
        );

      case 'date':
        return (
          <input
            type="date"
            id={field.id}
            value={(value as string) || ''}
            onChange={(e) => handleChange(field.id, e.target.value || null)}
            className={`${styles.input} ${error ? styles.inputError : ''}`}
            disabled={disabled}
            required={field.required}
          />
        );

      default:
        return null;
    }
  };

  // Group fields by section
  const sections = schema.sections || [];
  const fieldsBySection: Record<string, QuestionnaireField[]> = {};
  const unsectionedFields: QuestionnaireField[] = [];

  schema.fields.forEach((field) => {
    if (field.section) {
      if (!fieldsBySection[field.section]) {
        fieldsBySection[field.section] = [];
      }
      fieldsBySection[field.section].push(field);
    } else {
      unsectionedFields.push(field);
    }
  });

  return (
    <div className={styles.questionnaire}>
      {schema.title && <h2 className={styles.title}>{schema.title}</h2>}
      {schema.description && (
        <p className={styles.description}>{schema.description}</p>
      )}

      {/* Render sectioned fields */}
      {sections.map((section) => (
        <div key={section.id} className={styles.section}>
          <h3 className={styles.sectionTitle}>{section.title}</h3>
          {section.description && (
            <p className={styles.sectionDescription}>{section.description}</p>
          )}
          {fieldsBySection[section.id]?.map((field) => (
            <div key={field.id} className={styles.field}>
              <label htmlFor={field.id} className={styles.label}>
                {field.label}
                {field.required && <span className={styles.required}>*</span>}
              </label>
              {field.description && (
                <p className={styles.fieldDescription}>{field.description}</p>
              )}
              {renderField(field)}
              {errors[field.id] && (
                <p className={styles.error}>{errors[field.id]}</p>
              )}
            </div>
          ))}
        </div>
      ))}

      {/* Render unsectioned fields */}
      {unsectionedFields.length > 0 && (
        <div className={styles.section}>
          {unsectionedFields.map((field) => (
            <div key={field.id} className={styles.field}>
              <label htmlFor={field.id} className={styles.label}>
                {field.label}
                {field.required && <span className={styles.required}>*</span>}
              </label>
              {field.description && (
                <p className={styles.fieldDescription}>{field.description}</p>
              )}
              {renderField(field)}
              {errors[field.id] && (
                <p className={styles.error}>{errors[field.id]}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
